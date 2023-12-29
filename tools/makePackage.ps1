Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-LateMin  # power shell is very inconvenient
Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-GenShin  # power shell is very inconvenient
Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-MgenPlus  # power shell is very inconvenient
Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-MgenPlus2pp  # power shell is very inconvenient
Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-Text  # power shell is very inconvenient
mkdir -Force Packages/CorrectLocalizationJP-LateMin/CorrectLocalizationJPFont-LateMin
mkdir -Force Packages/CorrectLocalizationJP-LateMin/CorrectLocalizationJP-Text
mkdir -Force Packages/CorrectLocalizationJP-GenShin/CorrectLocalizationJPFont-Genshin
mkdir -Force Packages/CorrectLocalizationJP-GenShin/CorrectLocalizationJP-Text
mkdir -Force Packages/CorrectLocalizationJP-MgenPlus/CorrectLocalizationJPFont-MgenPlus
mkdir -Force Packages/CorrectLocalizationJP-MgenPlus/CorrectLocalizationJP-Text
mkdir -Force Packages/CorrectLocalizationJP-MgenPlus2pp/CorrectLocalizationJPFont-MgenPlus2pp
mkdir -Force Packages/CorrectLocalizationJP-MgenPlus2pp/CorrectLocalizationJP-Text
mkdir -Force Packages/CorrectLocalizationJP-Text
#Copy-Item -Recurse -Force Modules/CLJP-Common/* Packages/CorrectLocalizationJP-LateMin
#Copy-Item -Recurse -Force Modules/CLJP-Common/* Packages/CorrectLocalizationJP-GenShin

Copy-Item -Force doc/README.md Modules/CLJP-Common/README.md

Copy-Item -Recurse -Force Modules/CLJP-Font-GenShinGothic/* Packages/CorrectLocalizationJP-GenShin/CorrectLocalizationJPFont-Genshin
Copy-Item -Recurse -Force Modules/CLJP-Common/* Packages/CorrectLocalizationJP-GenShin/CorrectLocalizationJP-Text
Copy-Item -Force Modules/CLJP-Common/README.md Packages/CorrectLocalizationJP-GenShin/CorrectLocalizationJPFont-Genshin/
Copy-Item -Force Modules/CLJP-Common/LICENSE Packages/CorrectLocalizationJP-GenShin/CorrectLocalizationJPFont-Genshin/

Copy-Item -Recurse -Force Modules/CLJP-Font-LateMin/* Packages/CorrectLocalizationJP-LateMin/CorrectLocalizationJPFont-LateMin
Copy-Item -Recurse -Force Modules/CLJP-Common/* Packages/CorrectLocalizationJP-LateMin/CorrectLocalizationJP-Text
Copy-Item -Force Modules/CLJP-Common/README.md Packages/CorrectLocalizationJP-LateMin/CorrectLocalizationJPFont-LateMin/
Copy-Item -Force Modules/CLJP-Common/LICENSE Packages/CorrectLocalizationJP-LateMin/CorrectLocalizationJPFont-LateMin/

Copy-Item -Recurse -Force Modules/CLJP-Font-MgenPlus/* Packages/CorrectLocalizationJP-MgenPlus/CorrectLocalizationJPFont-MgenPlus
Copy-Item -Recurse -Force Modules/CLJP-Common/* Packages/CorrectLocalizationJP-MgenPlus/CorrectLocalizationJP-Text
Copy-Item -Force Modules/CLJP-Common/README.md Packages/CorrectLocalizationJP-MgenPlus/CorrectLocalizationJPFont-MgenPlus/
Copy-Item -Force Modules/CLJP-Common/LICENSE Packages/CorrectLocalizationJP-MgenPlus/CorrectLocalizationJPFont-MgenPlus/

Copy-Item -Recurse -Force Modules/CLJP-Font-MgenPlus2pp/* Packages/CorrectLocalizationJP-MgenPlus2pp/CorrectLocalizationJPFont-MgenPlus2pp
Copy-Item -Recurse -Force Modules/CLJP-Common/* Packages/CorrectLocalizationJP-MgenPlus2pp/CorrectLocalizationJP-Text
Copy-Item -Force Modules/CLJP-Common/README.md Packages/CorrectLocalizationJP-MgenPlus2pp/CorrectLocalizationJPFont-MgenPlus2pp/
Copy-Item -Force Modules/CLJP-Common/LICENSE Packages/CorrectLocalizationJP-MgenPlus2pp/CorrectLocalizationJPFont-MgenPlus2pp/

Copy-Item -Recurse -Force Modules/CLJP-Common/* Packages/CorrectLocalizationJP-Text

Compress-Archive -Force Packages/CorrectLocalizationJP-GenShin Packages/CorrectLocalizationJP-GenShin.zip
Compress-Archive -Force Packages/CorrectLocalizationJP-LateMin Packages/CorrectLocalizationJP-LateMin.zip
Compress-Archive -Force Packages/CorrectLocalizationJP-MgenPlus Packages/CorrectLocalizationJP-MgenPlus.zip
Compress-Archive -Force Packages/CorrectLocalizationJP-MgenPlus2pp Packages/CorrectLocalizationJP-MgenPlus2pp.zip
Compress-Archive -Force Packages/CorrectLocalizationJP-Text Packages/CorrectLocalizationJP-Text.zip
#Get-ChildItem Modules | ForEach-Object {
#    if ( -not ($_.Name.Substring(0, 5) -eq 'CLJP-')){
#        Write-Output $_.Name
#        Compress-Archive -Force Modules/$($_.Name)/ Packages/$($_.Name)JP.zip
#    }
#}
#Remove-Item -erroraction silentlycontinue -Recurse Packages/CorrectTextJP
#mkdir -Force Packages/CorrectTextJP
#Get-ChildItem Modules | ForEach-Object {
#    if ( -not ($_.Name.Substring(0, 5) -eq 'CLJP-')){
#        Write-Output $_.Name
#        Copy-Item -Force -Recurse Modules/$($_.Name) Packages/CorrectTextJP/
#    }
#}
#Compress-Archive -Force Packages/CorrectTextJP Packages/CorrectTextJP.zip