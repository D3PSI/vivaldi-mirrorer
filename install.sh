#!/bin/bash
cp mirrorer.service /etc/systemd/system
systemctl daemon-reload
systemctl enable --now mirrorer
