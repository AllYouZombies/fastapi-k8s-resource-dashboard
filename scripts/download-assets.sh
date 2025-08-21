#!/bin/bash

# Script to download external CDN resources for offline use
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Downloading external assets for offline use...${NC}"

# Create assets directory
mkdir -p app/static/lib/{bootstrap,fontawesome,datatables,chartjs}

# Bootstrap CSS
echo -e "${GREEN}✓${NC} Downloading Bootstrap CSS..."
curl -s -o app/static/lib/bootstrap/bootstrap.min.css \
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"

# Bootstrap JS
echo -e "${GREEN}✓${NC} Downloading Bootstrap JS..."
curl -s -o app/static/lib/bootstrap/bootstrap.bundle.min.js \
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"

# Font Awesome CSS
echo -e "${GREEN}✓${NC} Downloading Font Awesome CSS..."
curl -s -o app/static/lib/fontawesome/all.min.css \
  "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"

# Font Awesome Webfonts
echo -e "${GREEN}✓${NC} Downloading Font Awesome webfonts..."
mkdir -p app/static/lib/fontawesome/webfonts
for font in fa-solid-900.woff2 fa-regular-400.woff2 fa-brands-400.woff2; do
  curl -s -o "app/static/lib/fontawesome/webfonts/$font" \
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/$font"
done

# Chart.js
echo -e "${GREEN}✓${NC} Downloading Chart.js..."
curl -s -o app/static/lib/chartjs/chart.min.js \
  "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js"

# DataTables CSS
echo -e "${GREEN}✓${NC} Downloading DataTables CSS..."
curl -s -o app/static/lib/datatables/dataTables.bootstrap5.min.css \
  "https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css"

# jQuery (required for DataTables)
echo -e "${GREEN}✓${NC} Downloading jQuery..."
curl -s -o app/static/lib/datatables/jquery-3.7.1.min.js \
  "https://code.jquery.com/jquery-3.7.1.min.js"

# DataTables JS
echo -e "${GREEN}✓${NC} Downloading DataTables JS..."
curl -s -o app/static/lib/datatables/jquery.dataTables.min.js \
  "https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"

curl -s -o app/static/lib/datatables/dataTables.bootstrap5.min.js \
  "https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"

echo -e "\n${GREEN}🎉 All assets downloaded successfully!${NC}"
echo "Total size: $(du -sh app/static/lib | cut -f1)"

# Fix Font Awesome CSS paths
echo -e "${GREEN}✓${NC} Fixing Font Awesome CSS paths..."
sed -i 's|../webfonts/|webfonts/|g' app/static/lib/fontawesome/all.min.css

echo -e "\n${BLUE}📋 Next steps:${NC}"
echo "1. Run this script: ./scripts/download-assets.sh"
echo "2. Update base.html to use local assets"
echo "3. Test that all functionality works offline"