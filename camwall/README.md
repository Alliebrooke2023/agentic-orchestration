# CamWall
Multi-box camera wall + remote control + recording.

Run (Windows): `run.bat`  |  Sandbox: `python camwall.py --demo 4`
Remote: open the `http://<pc-ip>:8765/?t=...` link it prints (a random token is made if you do not pass `--token SECRET`). `--host 127.0.0.1` = this PC only, no token.

Sources: USB, DVI/HDMI capture cards (UVC index 0,1,..), Cortex cam / IoT cams
(rtsp://, http:// MJPEG, ONVIF auto-discovery), Bluetooth scan (BLE list only;
BT cams stream over Wi-Fi/RTSP). Recordings go to `recordings/`.
Untested on real hardware.
