Remove-Item -Recurse Packages/CorrectLocalizationJP-LateMin  # power shell is very inconvenient
Remove-Item -Recurse Packages/CorrectLocalizationJP-GenShin  # power shell is very inconvenient
mkdir -Force Packages/CorrectLocalizationJP-LateMin
mkdir -Force Packages/CorrectLocalizationJP-GenShin
Copy-Item -Recurse -Force Modules/Common/* Packages/CorrectLocalizationJP-LateMin
Copy-Item -Recurse -Force Modules/Common/* Packages/CorrectLocalizationJP-GenShin
Copy-Item -Recurse -Force Modules/Font-GenShinGothic/* Packages/CorrectLocalizationJP-GenShin
Copy-Item -Recurse -Force Modules/Font-LateMin/* Packages/CorrectLocalizationJP-LateMin
Compress-Archive -Force Packages/CorrectLocalizationJP-GenShin Packages/CorrectLocalizationJP-GenShin.zip
Compress-Archive -Force Packages/CorrectLocalizationJP-LateMin Packages/CorrectLocalizationJP-LateMin.zip