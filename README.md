# Assistant Lab

Build Your Own Smart Assistant — pygame game with multiplayer chat, trading, and cosmetics.

## Quick install (curl)

```bash
curl -fsSL https://raw.githubusercontent.com/OwendoyalAdastra-lang/assistant-lab/main/install.sh | bash
```

Or download zip:

```bash
curl -fsSL -o assistant-lab.zip https://github.com/OwendoyalAdastra-lang/assistant-lab/archive/refs/heads/main.zip
unzip assistant-lab.zip
cd assistant-lab-main
pip install -r requirements.txt
./run.sh server   # terminal 1
./run.sh game     # terminal 2
```

## Run

```bash
pip install -r requirements.txt
./run.sh server   # chat / trade / Social Lab (port 9876)
./run.sh game     # main game
```

## Controls

| Key | Action |
|-----|--------|
| C | Chat |
| T | Trade |
| L | Social Lab |
| , | Settings |
| F11 | Fullscreen |

## Multiplayer

**Local testing** (same computer): `./run.sh server` works on `127.0.0.1` with no key.

**Public / LAN server for others:** verify your email at the [Host Portal](https://assistant-lab-host.onrender.com), get a **Host Key**, then:

```bash
ASSISTANT_LAB_HOST_TOKEN=your_key_here ./run.sh server
```

Host keys let you run chat/trade/Social Lab — **not** admin (no free credits or items).

**Lab owner** uses the private `assistant-lab-owner/` folder on their machine only — never published to GitHub.

## Repo

https://github.com/OwendoyalAdastra-lang/assistant-lab