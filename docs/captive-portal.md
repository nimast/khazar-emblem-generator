# Captive Portal / First-Boot Provisioning

This document covers the **comitup** captive-portal setup that lets a new owner
configure WiFi on the Pi without SSH, keyboard, or monitor — just a phone.

## What this gives you

When the Pi boots and **can't reach any known WiFi network**, it falls back to
broadcasting its own open WiFi network. You connect a phone to that network,
a captive portal pops up, you pick your home WiFi from a list, enter the
password, and the Pi joins it. After that, the device runs normally on your
network.

## How to use it (recipient flow)

1. **Plug in the Pi.** Wait ~90 seconds for it to fully boot and decide that
   no known WiFi is reachable.
2. **On your phone, open WiFi settings.** Look for an open network called
   **`comitup-204`** (the number may differ — it's derived from the Pi's MAC
   address). Connect to it. No password.
3. **A captive portal should pop up automatically** (most phones detect it).
   If not, open a browser and visit `http://10.41.0.1`.
4. **Pick your WiFi from the list,** enter the password, submit.
5. The Pi switches to your network. The amulet display will resume rendering
   within a couple of minutes.

That's it. The credentials are saved on the Pi, so future power-cycles will
auto-rejoin without needing the captive portal again.

## How it's installed (Pi-side, one-time)

Done already on this Pi. Recorded for future reference:

```bash
# 1. Add the comitup APT repository via Davesteele's self-installing deb
curl -fsSL -o /tmp/comitup-apt.deb \
  https://davesteele.github.io/comitup/deb/davesteele-comitup-apt-source_1.3_all.deb
sudo dpkg -i --force-all /tmp/comitup-apt.deb

# 2. Install comitup
sudo apt update
sudo apt install -y comitup

# 3. Service auto-starts. Verify:
systemctl status comitup
```

The service runs on every boot, watches NetworkManager. When no known
networks are connected within ~60s, it activates AP mode and serves the
captive portal at `http://10.41.0.1`.

## Configuration

File: `/etc/comitup.conf` (currently using defaults).

Important defaults:

- **AP SSID:** `comitup-NNNN` where `NNNN` comes from the MAC address (this
  Pi advertises `comitup-204`)
- **AP password:** none — open network. The captive portal handles auth at
  the WiFi-provisioning level.
- **Captive portal address:** `http://10.41.0.1`
- **Mode:** `single` (only one AP fallback profile maintained)

To change the AP name, password, or other behavior, edit `/etc/comitup.conf`
and `sudo systemctl restart comitup`.

## Testing the full flow

To validate that comitup works correctly without risking the device, the test
sequence is:

```bash
# 1. List saved wireless profiles
nmcli -t -f NAME,TYPE,AUTOCONNECT connection show | grep wireless

# 2. Delete all real ones (keep comitup-204-0000 — that's comitup's own profile)
sudo nmcli connection delete "<each-other-profile>"

# 3. Reboot. Pi boots with no known networks reachable.
sudo reboot

# 4. Watch your phone's WiFi list. comitup-204 should appear within 60-90s.
# 5. Connect, captive portal opens, pick your WiFi, submit.
# 6. SSH back in via the new network to verify the driver is running:
ssh pi@inkypi.local 'pgrep -af "python -m khazar"'
```

## Failure modes

**Comitup never activates after reboot.** Either a saved profile is still
auto-connecting (check `nmcli connection show`), or the service crashed
(`systemctl status comitup`). The comitup-204 profile in `nmcli` is comitup's
own AP fallback — that's expected and shouldn't be deleted.

**`comitup-204` shows up but captive portal doesn't pop.** Phone may have
disabled captive-portal detection. Open a browser manually and visit
`http://10.41.0.1` or `http://comitup-204.local`.

**Pi joins the new WiFi but driver doesn't restart.** Known transient failure
mode if the boot-time `git pull` runs before WiFi is up — the driver's
`@reboot` cron is wrapped in `(git pull || true)` to prevent this from
blocking startup, but a manual restart is still:

```bash
ssh pi@inkypi.local 'pkill -f khazar_emblem; cd ~/khazar-emblem-generator && (nohup ~/.virtualenvs/pimoroni/bin/python -m khazar_emblem.driver >> driver.log 2>&1 </dev/null & disown -h)'
```

## Reset to factory captive-portal state

If you need the Pi to go back to "fresh-out-of-the-box" provisioning state:

```bash
# Delete every saved profile except comitup's own
nmcli -t -f NAME,TYPE connection show | grep wireless | grep -v comitup | cut -d: -f1 | \
  while read name; do sudo nmcli connection delete "$name"; done

sudo reboot
```

On next boot it'll behave exactly as a new device — no known networks,
comitup activates, captive portal flow.
