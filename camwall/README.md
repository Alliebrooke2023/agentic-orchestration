# CamWall
Multi-box camera wall + remote control + recording.

Run (Windows): `run.bat`  |  Sandbox: `python camwall.py --demo 4`
Remote: run prints a private link with a token (`?t=...`); open it on your phone. Every route requires the token; keep the link private.

Sources: USB, DVI/HDMI capture cards (UVC index 0,1,..), Cortex cam / IoT cams
(rtsp://, http:// MJPEG, ONVIF auto-discovery), Bluetooth scan (BLE list only;
BT cams stream over Wi-Fi/RTSP). Recordings go to `recordings/`.
Untested on real hardware.
