# CamWall
Multi-box camera wall + remote control + recording.

Run (Windows): `run.bat`  |  Sandbox: `python camwall.py --demo 4`
Remote: open `http://<pc-ip>:8765` on phone. Add `--token SECRET` to lock it.

Sources: USB, DVI/HDMI capture cards (UVC index 0,1,..), Cortex cam / IoT cams
(rtsp://, http:// MJPEG, ONVIF auto-discovery), Bluetooth scan (BLE list only;
BT cams stream over Wi-Fi/RTSP). Recordings go to `recordings/`.
Untested on real hardware.
