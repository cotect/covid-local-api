


Convert to swagger 2.0 specs via [api-spec-converter](https://github.com/LucyBot-Inc/api-spec-converter):

```
api-spec-converter --from openapi_3 --to swagger_2 --syntax yaml --check ./openapi.json > cotect_swagger2.yaml
```


Test API locally:
```
pip install -e .
cd ./covid_local_api && uvicorn local_test:app --reload
```
