./bin/python main.py \
  --key-file credentials/service-account.json \
  --urls urls.csv \
  --property-id 427363317 \
  --generate-doc \
  --doc-language fr \
  --google-credentials credentials/client_secret.json \
  --doc-title "Rapport d'analyse mensuel" 
> output.txt
