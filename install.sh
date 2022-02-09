#!/bin/bash
ln -s mirrorer.service /etc/systemd/system
systemctl --user daemon-reload
systemctl --user enable --now mirrorer.py
