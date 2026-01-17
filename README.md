# pip-dance
Piper AgileX robo arm dancer

## Raspberry Pi

| Property | Value |
|----------|-------|
| Hostname | `raspi` |
| User / Pass | `pi3` / `pi3` |
| IP (ethernet) | `192.168.2.3` |
| WiFi | `MikePhone` / `HardPassword` |
| SSH | Enabled |
| Pi Connect | Enabled |

## Connect via Ethernet (Mac)

**Hardware:** Mac → MOKiN USB-C hub → Pi (ethernet + microUSB power)

**Setup:**
1. System Settings → General → Sharing → Internet Sharing
   - Share from: **Wi-Fi**
   - To: **AX88179A** + **USB 10/100/1000 LAN** (both enabled)
   - Turn ON
2. Allow `dhcp6d` firewall prompt
3. **macOS 15+ (Sequoia):** System Settings → Privacy & Security → Local Network → Enable your terminal app

**Connect:**
```bash
ssh pi3@192.168.2.3
```

**Verify:**
```bash
ifconfig en9 | grep status    # should show "active"
ping 192.168.2.3              # should respond
```

## Connect via WiFi

Pi auto-connects to `MikePhone` hotspot when available.
```bash
ssh pi3@raspi.local
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `en9` status: inactive | No ethernet link | Reconnect cables, toggle Internet Sharing off/on |
| "No route to host" | macOS blocking local network | Privacy & Security → Local Network → Enable terminal |
| mDNS not resolving | Avahi not ready | Use IP `192.168.2.3` directly |
| traceroute works, ping/SSH don't | macOS Sequoia privacy | Same as "No route to host" fix |

## Fallback Access

[Raspberry Pi Connect](https://connect.raspberrypi.com/) - browser-based access when local network fails
