#!/bin/bash

# Remove a resposta anterior se existir
rm -f output/resposta.html


# Ativa o ambiente virtual
source ./venv/bin/activate;

pip install requirements.txt;

# Executa o script Python
python main.py
