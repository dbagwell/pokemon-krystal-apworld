#!/bin/sh

cp -r . pokemon_krystal
zip -r pokemon_krystal.apworld pokemon_krystal -x "*.DS_Store" -x "*.sh" -x "*.apworld" -x "*/.*"
rm -rf pokemon_krystal