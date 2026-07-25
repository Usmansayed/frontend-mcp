# ForOpenCode Gemini pipeline

Phased corpus builder: **deterministic scrape** + **Gemini (ADC/Vertex) synthesis**.

## Setup

```powershell
gcloud auth application-default login
$env:GOOGLE_CLOUD_PROJECT = "your-project-id"   # or rely on ADC project
$env:GOOGLE_CLOUD_LOCATION = "us-central1"      # optional
$env:FOROPENCODE_GEMINI_MODEL = "gemini-2.5-pro"  # or gemini-3.1-pro if available
pip install google-genai jsonschema beautifulsoup4 html2text
```

## Run

```powershell
# From repo root
python scripts/run_foropencode_pipeline.py --phase smoke
python scripts/run_foropencode_pipeline.py --phase scrape
python scripts/run_foropencode_pipeline.py --phase extract
python scripts/run_foropencode_pipeline.py --phase normalize
python scripts/run_foropencode_pipeline.py --phase compose
python scripts/run_foropencode_pipeline.py --phase graph
python scripts/run_foropencode_pipeline.py --phase validate

# Or all in order (stops on first failure)
python scripts/run_foropencode_pipeline.py --phase all
```

## Pass1 sources

See `pass1_sources.yaml` — Steering Law, Gestalt proximity (NN/g), NASA-TLX.

Gemini never writes unvalidated JSON: failures land in `ForOpenCode/10_quality/drafts/`.
