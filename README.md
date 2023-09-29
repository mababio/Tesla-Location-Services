# Tesla-Location-Services
Using TeslaPy Python module to build out Tesla location services

# Summary
Using [TeslaPy](https://github.com/tdorssers/TeslaPy) Python module to build 3 Services(Get_Location, Get_Proximity, Save_Location). These Services are
used by [Tesla Automation Platform](https://github.com/mababio/Tesla-Automation-Platform)

# Setup For GCP
- Set up GCP project, and IAM service accounts
- Tesla Credential: Find out how to generate cache.json Tesla credential file [here](https://github.com/tdorssers/TeslaPy)


# Optional
- [Secret Manager](secret_manager.py): You can choose to store your cache.json file in GCP Secret manager or store it locally. You can use secret_manager.py script to assist with this.
- [Cloud Build](cloudbuild.yaml): can use [cloudbuild.yaml](cloudbuild.yaml) to build out the Cloud Function.
