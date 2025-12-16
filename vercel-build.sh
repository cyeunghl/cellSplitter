#!/bin/bash
echo "Copying static files for Vercel..."
mkdir -p public
cp -r api/static/* public/
