=====================================================
llm-companion: A Self-Hosted AI Coding Assistant
=====================================================

:date: 2026-06-23 21:00
:modified: 2026-06-23 21:00
:tags: self-hosting, llm, ollama, podman, kubernetes, ansible, opencode, privacy, article
:category: Self-Hosting
:slug: llm-companion-self-hosted-ai-coding-assistant
:authors: tperrot
:summary: llm-companion is a rootless Podman Kubernetes Pod stack that
	  runs Ollama on a spare Fedora or Debian box and serves it to OpenCode.
	  Design choices and deployment steps.
:lang: en
:status: published

**I did not want my code to leave my network.** An agentic coding session
sends file contents, project structure and half-finished thoughts to whatever
model answers the prompts. I did not want that going to a third-party API by
default: it costs money for routine work, it stops when the LAN or VPN has no
route to the internet, and it teaches me nothing about serving an LLM on
constrained hardware. So I built `llm-companion`_, a rootless Ollama stack for
Fedora Server and Debian. It runs on a spare machine at home, `OpenCode`_
points at it, and cloud providers are only an explicit fallback.

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

* `Ollama`_ serves the models.
* `Open WebUI`_ is the browser chat interface. It keeps its own user
  accounts and history, and takes document uploads for RAG without a
  separate vector store.
* `SearXNG`_ is a metasearch engine that gives the chat agent web search
  without sending the query to a single third party.
* Open Terminal gives the agent a sandboxed shell, reachable from the
  browser.
* `Caddy`_ is the reverse proxy, the only container exposed to the host
  network, and the only place a Bearer token is enforced. It is also the only
  one that would need TLS, so adding HTTPS later is a Caddyfile change.

Two use cases: chatting through Open WebUI, and routing `OpenCode`_ sessions
through Ollama's OpenAI-compatible API.

Why It Is Built This Way
=========================

**One Pod, one exposed port.** All five containers share a single network
namespace and talk to each other over ``localhost``, not DNS names. Only Caddy
publishes a ``hostPort``. The firewall rule is one line (``8080/tcp``) and
authentication lives in one place, the Caddyfile. Open WebUI and Open Terminal
are never reachable directly, even from the LAN.

**Bearer auth at the proxy, not in each service.** Ollama and SearXNG have no
authentication of their own. Caddy checks a Bearer token before forwarding to
``/ollama/api/*``, ``/ollama/v1/*`` or ``/searxng/*``. Open WebUI keeps its own
login. Rotating the key (``generate-api-key.sh``) touches one Kubernetes
Secret, not three services' configs.

**A hardware-aware model picker instead of a fixed model list.**
``pull-models.sh`` detects architecture (x86_64/aarch64), accelerator (CPU,
AMD ROCm, NVIDIA CUDA) and available RAM/VRAM, then picks the best model that
fits for each category (coding, vision, general, embedding). That is a 1.5B
coding model and a 1.7B reasoning model on a 2 GB ARM64 board, Devstral Small 2
24B on a 16 GB+ GPU. ``--list`` shows the plan before pulling anything.

**Quadlet over a bare ``podman run``.** A Quadlet ``.kube`` unit gives the pod
normal systemd semantics: ``systemctl --user restart llm-companion``, restart
on failure, and ``AutoUpdate=registry`` so a ``podman auto-update`` timer pulls
newer pinned images. It runs rootless, with ``loginctl linger`` so the user
service survives without a login session.

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

I iterate on the stack this way: rebuild the golden image, boot, check the
services, tear down.

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

In order, it creates the directories and enables linger (``common``), opens
port 8080 via firewalld or ufw (``firewall``), installs Podman and builds the
Ollama image (``podman``), then generates the API key, installs ``stack.yml``
and starts the systemd service (``llm-stack``). It is idempotent: re-run it
after changing the inventory or pulling new code.

Pull models sized to your hardware:

.. code-block:: bash

   ./scripts/pull-models.sh --list    # dry run: show what would be pulled
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
provider in the same config and are selected with the same ``/models``
command. That is the fallback: local by default, cloud when I am travelling,
the model is too large for the box, or the service is down.

Lessons Learned
================

Rootless GPU access was the hard part. ROCm needs ``/dev/kfd`` and
``/dev/dri`` inside the container, which needs ``securityContext.privileged:
true``; I found no narrower rootless path to those device nodes. The ROCm
variant therefore gives up some of the isolation the CPU variant has. It is a
separate manifest (``stack-rocm.yml``), not a flag on the default one, and the
host should be dedicated to it.

The model picker mattered more than I expected. Picking a quantization by hand
works for one machine. It breaks when the same playbook must run unchanged on a
2 GB ARM64 board, an 8 GB CPU-only Fedora box and a 16 GB GPU desktop. With the
RAM/VRAM gates in one script, the Ansible roles, the Quadlet unit and the Caddy
config do not need to know which tier they run on.

.. _llm-companion: https://github.com/tprrt/llm-companion
.. _OpenCode: https://opencode.ai
.. _Ollama: https://ollama.com
.. _Open WebUI: https://github.com/open-webui/open-webui
.. _SearXNG: https://github.com/searxng/searxng
.. _Caddy: https://caddyserver.com
.. _vm.sh: https://github.com/tprrt/llm-companion/blob/master/scripts/vm.sh
