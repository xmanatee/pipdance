# pip-dance
Piper AgileX robo arm dancer

## Raspberry Pi Connection

| Property | Value |
|----------|-------|
| Hostname | `raspi` |
| Username | `pi3` |
| Password | `pi3` |
| WiFi SSID | `MikePhone` |
| WiFi Password | `HardPassword` |
| SSH | Enabled |
| Raspberry Pi Connect | Enabled |

### Connecting via Ethernet (Mac Internet Sharing)

1. Connect Mac to Raspberry Pi via USB ethernet adapter (MOKiN hub)
2. Enable Internet Sharing: System Settings → General → Sharing → Internet Sharing
   - Share from: Wi-Fi
   - To: AX88179A and USB 10/100/1000 LAN
3. Pi will get IP on 192.168.2.x subnet
4. Connect: `ssh pi3@raspi.local`

### Connecting via WiFi

The Pi is configured to connect to `MikePhone` WiFi network.
Connect: `ssh pi3@raspi.local`
