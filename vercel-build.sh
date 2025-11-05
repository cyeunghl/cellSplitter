#!/bin/bash
# Copy static files from api/static to root/static for Vercel to serve directly
mkdir -p static
cp -r api/static/* static/
