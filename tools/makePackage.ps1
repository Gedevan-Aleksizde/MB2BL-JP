Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-LateMin  # power shell is very inconvenient
Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-GenShin  # power shell is very inconvenient
Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-MgenPlus  # power shell is very inconvenient
Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-MgenPlus2pp  # power shell is very inconvenient
mkdir -Force Packages/CorrectLocalizationJP-LateMin
mkdir -Force Packages/CorrectLocalizationJP-GenShin/
mkdir -Force Packages/CorrectLocalizationJP-MgenPlus
mkdir -Force Packages/CorrectLocalizationJP-MgenPlus2pp

Copy-Item -Force doc/README.md Modules/CLJP-Common/README.md

Copy-Item -Recurse Modules/CLJP-Font-GenShinGothic/* Packages/CorrectLocalizationJP-GenShin
Copy-Item -Recurse Modules/CLJP-Common/* Packages/CorrectLocalizationJP-GenShin
Copy-Item Modules/CLJP-Common/README.md Packages/CorrectLocalizationJP-GenShin
Copy-Item Modules/CLJP-Common/LICENSE Packages/CorrectLocalizationJP-GenShin

Copy-Item -Recurse Modules/CLJP-Font-LateMin/* Packages/CorrectLocalizationJP-LateMin
Copy-Item -Recurse Modules/CLJP-Common/* Packages/CorrectLocalizationJP-LateMin
Copy-Item Modules/CLJP-Common/README.md Packages/CorrectLocalizationJP-LateMin
Copy-Item Modules/CLJP-Common/LICENSE Packages/CorrectLocalizationJP-LateMin

Copy-Item -Recurse Modules/CLJP-Font-MgenPlus/* Packages/CorrectLocalizationJP-MgenPlus
Copy-Item -Recurse Modules/CLJP-Common/* Packages/CorrectLocalizationJP-MgenPlus
Copy-Item Modules/CLJP-Common/README.md Packages/CorrectLocalizationJP-MgenPlus
Copy-Item Modules/CLJP-Common/LICENSE Packages/CorrectLocalizationJP-MgenPlus

Copy-Item -Recurse Modules/CLJP-Font-MgenPlus2pp/* Packages/CorrectLocalizationJP-MgenPlus2pp
Copy-Item -Recurse Modules/CLJP-Common/* Packages/CorrectLocalizationJP-MgenPlus2pp
Copy-Item Modules/CLJP-Common/README.md Packages/CorrectLocalizationJP-MgenPlus2pp
Copy-Item Modules/CLJP-Common/LICENSE Packages/CorrectLocalizationJP-MgenPlus2pp/

Compress-Archive -Force Packages/CorrectLocalizationJP-GenShin Packages/CorrectLocalizationJP-GenShin.zip
Compress-Archive -Force Packages/CorrectLocalizationJP-LateMin Packages/CorrectLocalizationJP-LateMin.zip
Compress-Archive -Force Packages/CorrectLocalizationJP-MgenPlus Packages/CorrectLocalizationJP-MgenPlus.zip
Compress-Archive -Force Packages/CorrectLocalizationJP-MgenPlus2pp Packages/CorrectLocalizationJP-MgenPlus2pp.zip
