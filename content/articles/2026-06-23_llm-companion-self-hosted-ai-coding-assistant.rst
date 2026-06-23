================================================================
llm-companion: A Self-Hosted, Privacy-First AI Coding Assistant
================================================================

:date: 2026-06-23 21:00
:modified: 2026-06-23 21:00
:tags: self-hosting, llm, ollama, podman, kubernetes, ansible, opencode, privacy, article
:category: Self-Hosting
:slug: llm-companion-self-hosted-ai-coding-assistant
:authors: tperrot
:summary: A look at llm-companion, a rootless Podman Kubernetes Pod stack
	  that turns a spare Fedora or Debian box into a private, hardware-aware
	  Ollama server for OpenCode — with a practical guide to deploying it.
:lang: en
:status: published

**I did not want my code to leave my network.** Every agentic coding session
sends a stream of file contents, project structure, and half-finished thoughts
to whatever model answers the prompts. Routing all of that through a third-party
API felt like the wrong default, even when the provider is trustworthy: it is
recurring cost for routine work, it stops working the moment the LAN or VPN
does not reach the internet, and it teaches me nothing about how the serving
side of an LLM stack actually behaves under constrained hardware. So I built
`llm-companion`_, a rootless Ollama stack for Fedora Server and Debian that I
can run on a spare machine at home and point `OpenCode`_ at, with cloud
providers wired in only as an explicit fallback rather than the default path.

This article walks through what the stack looks like, why it is built the way
it is, and how to deploy it yourself.

What llm-companion Is
======================

At its core, `llm-companion`_ is a single Kubernetes Pod manifest
(``kube/stack.yml``) deployed by Ansible, running five containers that share
one network namespace:

.. code-block:: text

   Internet / LAN / VPN
           │
        :8080  ← firewalld / ufw opens only this port
           │
   ┌────────────────────────────────────────────────────────┐
   │  llm-companion Pod  (shared network namespace)         │
   │                                                        │
   │  ┌──────────────────────────────────────────────────┐  │
   │  │  caddy  :8080 (hostPort)                         │  │
   │  │  Bearer token auth on /ollama/api/* /ollama/v1/* │  │
   │  │  Passes /searxng/* to SearXNG (Bearer token)     │  │
   │  │  Passes / to Open WebUI                          │  │
   │  └───────────────────┬──────────────────────────────┘  │
   │                      │ localhost                       │
   │  ┌───────────────────▼──┐  ┌───────────────────────┐   │
   │  │  ollama :11434       │  │  open-webui :3000     │   │
   │  │  (internal)          │  └────────┬──────────┬───┘   │
   │  └──────────────────────┘           │          │       │
   │                              ┌──────▼──┐  ┌────▼──────┐│
   │                              │ searxng │  │   open-   ││
   │                              │  :8888  │  │ terminal  ││
   │                              │         │  │  :8000    ││
   │                              └─────────┘  └───────────┘│
   └────────────────────────────────────────────────────────┘

`Ollama`_ serves the models, `Open WebUI`_ provides a chat interface with
document/RAG support, `SearXNG`_ gives the chat agent web search without
sending queries to a third party, and Open Terminal gives the agent a sandboxed
shell. `Caddy`_ is the only container exposed to the host network, and it
enforces a Bearer token on every API route.

`Open WebUI`_ is the browser-facing piece: besides the chat interface, it
keeps its own user accounts and conversation history, and lets you upload
documents for retrieval-augmented generation without standing up a separate
vector store just for that.

`SearXNG`_ is a self-hosted metasearch engine — it aggregates results from
other search engines and returns them without forwarding the query to any
single one of them, which is what lets the agent's web-search tool stay
consistent with the rest of the stack's no-third-party-by-default stance.

`Caddy`_ is the reverse proxy and, as noted above, the only place auth is
enforced — it is also the only container that would need to know about TLS,
so adding HTTPS later (if this ever leaves the LAN) is a Caddyfile change,
not a new container.

Open Terminal gives a sandboxed shell on the pod, reachable from the
browser — useful for checking logs or restarting a service without opening
a separate SSH session.

The whole thing targets two use cases: chatting through Open WebUI from a
browser, and routing `OpenCode`_'s agentic coding sessions through Ollama's
OpenAI-compatible API — the same workflow you would normally point at Claude
or GPT-4o, but served from hardware you control.

Why It Is Built This Way
=========================

A few decisions in the stack are not obvious from the README's quick-start, but
they are the part I actually learned something from.

**One Pod, one exposed port.** All five containers share a single network
namespace and talk to each other over ``localhost``, not DNS names. Only Caddy
publishes a ``hostPort``. This means the firewall rule is one line
(``8080/tcp``), and there is exactly one place — the Caddyfile — where
authentication is enforced. Open WebUI and Open Terminal are never reachable
directly, even from the LAN.

**Bearer auth at the proxy, not in each service.** Ollama and SearXNG have no
authentication of their own. Caddy terminates every request and checks a
Bearer token before forwarding to ``/ollama/api/*``, ``/ollama/v1/*``, or
``/searxng/*``. Open WebUI keeps its own login, since it already has user
accounts. Centralizing auth in the proxy means rotating the key
(``generate-api-key.sh``) only touches one Kubernetes Secret, not three
services' configs.

**A hardware-aware model picker instead of a fixed model list.** Self-hosted
LLM advice tends to assume either a beefy GPU or hand-picking quantizations
yourself. ``pull-models.sh`` detects architecture (x86_64/aarch64), accelerator
(CPU, AMD ROCm, NVIDIA CUDA), and available RAM/VRAM, then selects the best
model per category (coding, vision, general, embedding) that actually fits —
down to a 1.5B coding model and 1.7B reasoning model on a 2 GB ARM64 board, up
to Devstral Small 2 24B on a 16 GB+ GPU. ``--list`` shows the plan before
pulling anything.

**Quadlet over a bare ``podman run``.** The pod is managed by a Quadlet
``.kube`` unit, which gives it normal systemd semantics — ``systemctl --user
restart llm-companion``, automatic restart on failure, and
``AutoUpdate=registry`` so a ``podman auto-update`` timer can pull newer
pinned images without manual intervention. Rootless throughout, with
``loginctl linger`` so the user service survives without an active login
session — important for a box that is meant to just sit there and serve
requests.

Deploying It
============

The fastest way to see the stack end-to-end is `vm.sh`_, which provisions a
QEMU/KVM VM running the exact same Ansible playbook and ``kube/stack.yml`` used
on real hardware:

.. code-block:: bash

   sudo dnf install qemu-kvm qemu-img wget curl genisoimage
   sudo usermod -aG kvm $USER && newgrp kvm

   git clone https://github.com/tprrt/llm-companion
   cd llm-companion

   ./scripts/vm.sh build           # one-time provisioning (~golden image)
   ./scripts/vm.sh start           # boots in ~2 minutes from there on

This is how I iterate on the stack itself — rebuild the golden image after a
change, boot, check the services, tear down — without touching real hardware.

For an actual deployment, copy the example inventory and point it at your
server:

.. code-block:: bash

   cp ansible/inventory/hosts.yml.example ansible/inventory/hosts.yml
   $EDITOR ansible/inventory/hosts.yml

.. code-block:: yaml

   all:
     children:
       llm_companion:
         hosts:
           my-server:
             ansible_host: 192.168.1.100
             ansible_user: fedora
             ansible_ssh_private_key_file: ~/.ssh/id_ed25519

Then run the playbook:

.. code-block:: bash

   ansible-playbook -i ansible/inventory/hosts.yml ansible/site.yml

It handles, in order: required directories and linger (``common``), opening
port 8080 via firewalld or ufw (``firewall``), installing Podman and building
the Ollama image (``podman``), and generating the API key, installing
``stack.yml``, and starting the systemd service (``llm-stack``). It is
idempotent — re-run it any time you change the inventory or pull new code.

Pull models sized to your hardware:

.. code-block:: bash

   ./scripts/pull-models.sh --list    # dry run — see what would be pulled
   ./scripts/pull-models.sh           # pull the best model per category

On an AMD GPU host, re-run Ansible with ``-e "ollama_build_target=rocm"`` first
to build the ROCm image and deploy ``stack-rocm.yml`` instead, which grants the
container access to ``/dev/kfd`` and ``/dev/dri``.

Wiring Up OpenCode
===================

On the client machine, point `OpenCode`_ at the server through its
OpenAI-compatible provider config (``~/.config/opencode/opencode.json``):

.. code-block:: json

   {
     "$schema": "https://opencode.ai/config.json",
     "model": "ollama/qwen3-8b-16k",
     "provider": {
       "ollama": {
         "npm": "@ai-sdk/openai-compatible",
         "name": "Ollama",
         "options": {
           "baseURL": "http://<server-ip>:8080/ollama/v1",
           "headers": { "Authorization": "Bearer sk-ollama-<your-key>" }
         },
         "models": {
           "qwen3-8b-16k": { "name": "Qwen3 8B — coding/vision/general (16k)", "tools": true }
         }
       }
     }
   }

The key is printed at the end of the Ansible run and stored in
``~/.config/ollama/api-key.env`` on the server. Switch models at any time with
``/models`` inside OpenCode — no restart needed.

Cloud providers (Anthropic, GitHub Copilot) can sit alongside the ``ollama``
provider in the same config, switched to with the same ``/models`` command.
That is the fallback path I mentioned earlier: the local stack is the default,
and the cloud is one keystroke away when the network or the hardware cannot
keep up — travelling, a model too large for the box, or the service simply
being down.

Lessons Learned
================

Rootless GPU access was the part that fought back the most. ROCm needs
``/dev/kfd`` and ``/dev/dri`` inside the container, which in turn needs
``securityContext.privileged: true`` — there is no narrower rootless path to
those device nodes today, so the ROCm variant trades some of the isolation
the CPU variant gets for free. That trade-off is explicit in the stack
(``stack-rocm.yml`` is a separate manifest, not a flag on the default one),
and it is documented as a host that should be dedicated rather than shared.

The hardware-aware model picker turned out to matter more than I expected.
Hand-picking a quantization for "your" machine works fine for one machine; it
falls apart the moment the same playbook needs to run unchanged on a 2 GB
ARM64 board, an 8 GB CPU-only Fedora box, and a 16 GB GPU desktop. Encoding the
RAM/VRAM gates once, in one script, meant the rest of the stack — Ansible role,
Quadlet unit, Caddy config — never needed to know which tier it was running
on.

The other recurring theme: most of the actual engineering here is not in
Ollama at all, it is in the boring infrastructure around it — one auth
boundary, one exposed port, one systemd unit, one script that adapts to
whatever box it lands on. That boring part is also what makes me comfortable
leaving it running unattended.

.. _llm-companion: https://github.com/tprrt/llm-companion
.. _OpenCode: https://opencode.ai
.. _Ollama: https://ollama.com
.. _Open WebUI: https://github.com/open-webui/open-webui
.. _SearXNG: https://github.com/searxng/searxng
.. _Caddy: https://caddyserver.com
.. _vm.sh: https://github.com/tprrt/llm-companion/blob/master/scripts/vm.sh
