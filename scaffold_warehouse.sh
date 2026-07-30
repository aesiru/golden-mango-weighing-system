#!/bin/bash
# Scaffolds the warehouse module entities for the project.

set -e

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Scaffolding warehouse entities...${NC}"

cd "$(dirname "$0")/backend"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Please run install.sh or run.sh first."
    exit 1
fi

# Scaffold Entities
python -m app.forge new-entity company --module warehouse --fields "name:string,contact_infos:string"
python -m app.forge new-entity crate_class --module warehouse --fields "name:string,min_weight:float,max_weight:float"
python -m app.forge new-entity order --module warehouse --fields "company:link,crate_class:link,total_amount:float,current_amount:float"
python -m app.forge new-entity crate --module warehouse --fields "code:string,order:link,crate_class:link,target:float,counted:float"
python -m app.forge new-entity reading --module warehouse --fields "crate:link,weight_kg:float,recorded_at:date,valid:boolean"

echo -e "\n${GREEN}Syncing schema to the database...${NC}"
export PYTHONUTF8=1
python -m app.forge sync

echo -e "\n${GREEN}Generating TypeScript types for frontend...${NC}"
python -m app.forge generate-types

echo -e "\n${GREEN}Scaffolding complete!${NC}"
