# Correct Localization JP - Mount and Blade 2: Bannerlord Mod

ver. 0.9.0, 本体 ver. 1.0.3 に対応

## 概要

1. バニラで日本語設定にするとフォントあちこち文字化けするので文字化けしないフォントに置き換えます. いくつか種類を用意しました.
2. 日本語のテキストも変な箇所が多いので修正します. 本体のテキスト全体の約2万件のうち, 現在は **21%くらい**を修正しています.
	* 現時点では一般セリフはまだほとんど手を加えていないなど, まだ不完全な箇所が多いですが, メニュー画面でよく見られるUIやアイテム名等を重点的に変えたので印象はだいぶ変わると思います.
	* これ以降も何度かに分けて更新する予定です

アーリーアクセスの頃に似たようなことやってる人々の形跡は見つけましたが今公開されてて生きてる/まとまったものが見つからなかったので作りました.

## インストール方法

(初めてModを入れる人へ) NexusMods でダウンロードするにはNexusModsのアカウント登録が必要です. どうしてもアカウント登録したくない場合, github のほうからダウンロードしてください. 基本的にはどちらにも同じものを同時にアップロードするつもりですが, 手動作業なので忘れることもあるかもしれません.

通常の module の形式 (以下, Module 版)と, 本体ファイルを上書きするタイプ (以下, 上書き版) の2種類を用意しています. 前者は Main Files に, 後者は Optional Files にあります. ほとんどmodを入れない方は前者, modに慣れている人は後者がいいかもしれません. それぞれのタイプはさらに, 使用フォント違いでいくつかバリエーションを用意しています

### Module版

1. 通常のmodのインストールと同じです. 特殊な操作は必要ありません. Main Files の CorrectLocalizationJP-\* いずれか1つ (末尾は使用フォントによって変わります) をダウンロードし, M&B2 インストールフォルダにある Modules フォルダに入れて, ランチャーで有効にしてからM&B2を起動してください.
2. タイトル画面のオプション (Options) から,  「日本語」ではなく「正しい日本語」を選択してください. (スクロールすると下の方で見つかります)
   * (なお, そのすぐ下の "Voice Language" という項目名は本体の不具合で英語から変更できません)

### 上書き版

Optional Files の CorrectLocalizationJP-Overwrite-\* のいずれか1つをダウンロードし フォルダ内の複数のフォルダを上書きする形になり, また言語設定は「日本語」のままで適用されます.

M&B2は割とまだ不安定なことがあるので, 想定問答集とかトラブルシュートとかを下の方に書いています.

### 注意点

* Modを入れてプレイすると実績が解除されなくなります (現状, ゲームバランスを変更しないModであってもインストールすると実績解除が禁止されます).  実績解除が必要な場合, 以下のいずれかの方法で解決できます.
    1. [AchievementUn(bloc)ker](https://www.nexusmods.com/mountandblade2bannerlord/mods/4587) を同じようにインストールしてください. なくても動作しますが, 実績未解放で入れ忘れてたら悲しいので Nexus には Requirements として登録しています.
    2. Optional Files にある上書き版をコピーしてください. 名前に Overwriter とついているものです.
* マルチプレイモードも module としてインストールすると認識しません. マルチプレイの日本語も修正したい場合はやはり上書きが必要です. フォントはどちらでも変更できます. (ただし, マルチプレイ用のテキストの確認作業はまだ途中です)

現状, M&B2のmodは何故かわかりませんが 「新しい言語を登録することはできるが, 既存のテキストの修正はできない」という不可解な仕様なようなので, Module版では日本語の上書きではなく「正しい日本語」という別言語扱いになっています. 一方で本体ファイルを直接上書きすれば, 通常の「日本語」選択でもフォントとテキストが修正されます. どちらのインストール方法も一長一短だと思います (独立modはインストール時に一手間増える一方, 不具合があったときに差し戻しが容易, 上書きはアップデートした際に不具合が起こりやすい?)

余力があればHarmonyとか使ってもっと手軽に適用できるようにしたいですが, 期待はしないでください.

## Mod の詳細

### フォントの修正について

M&B2 本体は現在 (v1.0.3), おそらく常用漢字以外の漢字が使われており, ところにより文字化けしたり, スタイルの全く違う KaiTi フォントにフォールバックしたりして, かなり読みづらいです. そのため使用フォントを適切なものに置き換えます.

フォントはいくつかバリエーションを用意しました. 好きなものをどれか1つインストールしてください.

1. 「源真ゴシックP」 - バニラの日本語フォントに近い形状
2. 「源暎ラテミンP」 - 雰囲気重視

今後気分次第で増やすかもしれません. あるいは要望があったらやるかもしれません.

(1) に関しては, バニラ同様源ノ角ゴシック (Source Han Sans) を使いたかったのですが, 公式 Modding Kit の技術的制約により困難だったため, 「源真ゴシックP」を採用しました. しかし, 大部分は同じなので違和感はないと思います.  (2) の「源暎ラテミンP」は少し特徴的な線のフォントです. 線が太く強弱のない角ゴシックよりも, 欧文混じりのテキストに向いている気がしたので採用しました. 一方でウエイトが一種類だけなので, 表示箇所によっては字がやや詰まりすぎて見えることもあります. また, 個別のスタイルの問題で文字の配置が少しずれていたりはみ出したりする箇所がありますが, 修正が難しいので一旦保留としています

v1.0.3 現在, M&B2 本体に収録されている日本語のグリフはおそらくかなと常用漢字程度です. そのため「隼」「颯」「樽」といった漢字が文字化け(豆腐化)するか, もしくは中国語用の KaiTi フォントにフォールバックされます. (更にいうと, KaiTi は楷書でしかも基準の高さがズレてるのでかなり違和感があります.) 一方で, このmodに含まれているフォントはいずれもオリジナルの源ノ角ゴシックと同等のグリフを収録しているので, 通常の日本語で使われる文字 (かな, 漢字, いくつかの特殊記号) を表示するぶんには文字化けしないと思います (よって, modの日本語化とかでバニラで使われないような漢字が出てきても対応できると思います).

### 翻訳テキストの修正 (あるいは校正) について

v1.0.3現在, 大意は掴めますが, 全体的に不自然な日本語が多いです. このmodのタイトルは Correct Localization ですが, 狭義の誤訳より広い範囲を修正対象としています.

* 明確な誤訳 (時々あります)
* 誤字脱字 (わりとあります)
* そもそも元の英文からして間違ってるので訳文もおかしい (まれにあります)
* システムメッセージやアイテム名に見られる悪文 (とても多いです)
* かっこよくない (個人の感想です) ユニット名
    * むしろこれは校正というより翻案ですが, ユニット名はユニット名だけで1つのファイルで固まっていて修正は簡単なので気に入らない人はここだけ変えることもできます.
* 確認の必要な箇所が膨大なので今後も何度か修正版を更新するかもしれません.
* 校正内容の詳細は長くなったので別のとこに書きます. 修正の典型例は比較画像を見てください

表示箇所別に分けると, 以下のような進捗状況になっています. 数字は体感です.

1. メニュー画面, マップや戦闘時のステータス表示・ログ等のUI関連 - 90%, ほぼ完了
2. オプションの設定項目関連 - 50%くらい?
3. アイテム名・鍛冶の部品名 - 80%, おおむねできています, 一般的な表記ルールを整備するかもしれない
4. クエスト・会話セリフ・百科事典のテキスト - 10% 正しくない用語や誤字を機械的に置換した程度でほとんど手つかず
5. 固有名詞・汎用人名のスペル確認 - 0%
6. マルチプレイ - ??%, modが動作しない・そもそもあまりやってないため確認中

#### ゲームの用語の変更例

文脈によっては変わることがありますが, ステータス表示等では基本的に統一するようにしています. 特に紛らわしい変更箇所を抜粋します.

* Smelt/精錬 -> 溶解, または「鋳溶かす」
* Troops/中隊 -> 兵士, 部隊 (部隊を指すことも兵士一人ひとりを指すこともあるので文脈に応じて)
* Militia/民兵 -> 市民兵(団) (雇用できる兵士ユニットの民兵と各集落に配備される民兵を区別するため)
* Throwing/投てき -> 投擲
* Armor/(アーマー, 装甲, 防具, 防御値など場所によってバラバラ) -> 防御力
* Ranged/遠隔 -> 投射 (兵・武器)
* Garrison/駐屯地 -> 守備隊
* Notables/名士 -> 有力者
* Relationship/関係性 -> 好感(度)
* Prisoners/囚人 -> 捕虜
* Workshop/作業場 -> 工房
* Policy/方針 -> 国策
    * 国策名も雰囲気重視で多少翻案しています
* Men #/男 # -> 兵力 (ウケる)
* Hero/英雄 -> ヒーロー (一般名詞の英雄ではなく, プレイヤーキャラ, 雇用できる仲間, 名有りモブ領主のこと)
* Ransom Broker/受戻し仲介人 -> 人質取引商
* 戦闘関連は特に変なやつが多いです
    * Engage/婚約 -> 交戦
    * Loose/疎開 -> 散開 
    * Line/直線 -> 横隊
    * Circle/円 -> 円陣
    * Square/四角 -> 方陣
    * Scatter/散開とか散兵とかバラバラ -> 散兵線
    * Skein/鶴翼, V字などバラバラ -> 楔陣 (「雁行」ではやや紛らわしいので)
    * Formation -> 隊形・編隊 (命令コマンドの Formation は「隊形」, 戦闘開始時に編成し, 指揮官を割り当てたりする兵士のグループは「編隊」)
    * Radial/半径 -> 円形
    * Bar/バー -> 棒状
    * Four Part/四部構成 -> 十字型
    * Thrre Part/三部構成 -> 三叉型
    * disorganized state recovery -> 陣形再編
    * Delegate Command On(Off)/代理の指令 On(Off) -> 指揮の委任 On(Off) (悪いUIの典型例ですがテキスト変更だけではUIの改善まではできません)
    * 委任戦闘時のログや指揮官のセリフの悪文も修正してます
	* 各兵士クラスは主に上位のものを (RTSゲームでよくあるユニークユニットのように) 「〇〇の」を省略したり特徴的な名前に変更しています
    	* (Hidden Hand のみクラン名とユニット名のIDが使いまわされているので統一感がありません)

### ID の重複問題

M&B2 は本体だけでもいくつかのモジュールで構成されていますが, それら基本モジュールですら, 言語ファイルのIDがモジュール間で重複しているものがそれなりにあります (全体の30%程度) ほとんどは文字列が同じですが, さらにその内ごくわずか, 数十組程度ですが, モジュール毎に異なるテキストが割り当てられているものがあります. v1.0.3 現在, Native と SandBoxCore 間でのみ衝突が確認されているため, Native のテキストを優先しています. とはいえ, 違いの多くはスペルミスなのでそこまで大きな影響はありません.

## 想定問答集 (FAQ) とトラブルシュート


* Q.: マジで文字化けしなくなるの?
* A.: 通常の日本語であれば多分大丈夫です. 例えば仮に, modの翻訳文に「『颯』爽」「樽」「隼」「憂『鬱』」といった常用漢字外の字を追加したとしても表示されます. 厳密なテストはしていませんが, 源真ゴシックは 19,623, 源瑛ラテミンは 18,198 のグリフを収録しています. いずれもAJ1-6 に準拠した源ノ角ゴシックを元にしているため, 通常日本語で使われうる文字はほぼ全て対応していると考えて問題ないです. 逆に, 簡体字などは対応してないですが, AJ1-6のグリフ数でもけっこうギリギリだったので現状M&B2 の仕様に沿ってCJK統合漢字を全て同じスタイルで表示させるのは不可能だと思います.

* Q.: 他の日本語化modと併用できる?
* A.: 手間がかかることがありますが, 注意すれば可能です. Modを上書きして日本語化するタイプのファイルの場合,「日本語」と本modの「正しい日本語」は別言語扱いなので, 「正しい日本語」選択時にはModの日本語化がされない可能性があります. 翻訳ファイルの XML ファイルの id を全て "日本語" から "correct_正しい日本語" に修正するか (VS Code のフォルダ単位の置換機能とか使ってください), 本modの上書き版を使用すれば併用できると思います. 本体の日本語を変更するタイプのmodは, 場合によります. 私がNexusで見つけられたのはこれ1つだけで, このmodであれば本modの上書き版の後にさらに上書きすればユニット名だけ変わると思います. もしくは Module 版とうまく手作業で連結してください.

https://www.nexusmods.com/mountandblade2bannerlord/mods/2806

* Q.: ゲームが動かない, エラーが出て落ちる
* A.: 長いので折りたたみ. 

以下は私の個人的経験に基づくものなので, 完全ではないかもしれません. この mod とは関係ない, 本体のバグが原因であるケースもあるかもしれません.

ゲーム本体のバージョンと Mod にかかれている対応バージョンが一致しているか確認してください. 特に本体上書き版はバージョンが一致しない時の警告が出ない可能性が高いです. バージョンが違っても動作することはありますが, 保証はできません. こういう場合, ゲームがクラッシュする, 動作はするが日本語修正が部分的におかしい (一部英語だったり一部バニラの日本語のままだったり) など, 様々な不具合が想定され, 何が起こるかわかりません.

次に, ランチャーで全てのmodを無効化してから起動してみてください. これで動くなら, いずれかの mod が原因の可能性が高いです. もしそのmodが私のmodだけなら, 具体的な状況を教えていただけると助かります.

それでも問題が解決しない場合, 本体の再インストールが必要なときもあります. はじめは Steam の「整合性の確認」だけでも十分です. それでもだめなら再インストールしてみてください. その場合, Steamからアンインストールボタンを押した後にインストールフォルダに残っているファイルがあったらそれも削除してください. (インストールフォルダだけでいいです. セーブデータまで削除するのは「最後の手段」にしてください)

* Q.: 文字化けは回避したいけどお前の翻訳センスないから文章まで変えてほしくない
* A.: このModフォルダ内にある ModuleData フォルダを削除すると, テキストは変更されず, フォントだけが変更されます

* Q.: 翻訳テキストいらんとこまで変えないで
* A.: 固有名詞やスキル名も変えるとかえって混乱を招きそうなので, 選択制にするかもしれません

* Q.: フォントもいらないんだけど
* A.: このModフォルダ内にある GUI, AssetSources, Assets, RuntimeDataCache フォルダを削除すればフォント変更はされなくなります.

* Q.: RuntimeDataCache っていうやたらとサイズの大きいファイルがあるんだけどCacheって名前だしこれいらなくね?
* A.: これがないとフォントが正常に読み込まれません. なぜこのような仕様なのか私もよくわかりません.


## 補足/Notes

* NexusMods の掲示板には日本語が書き込めません. 日本語での不具合報告は GitHub か私のブログでお願いします. ただし, クラッシュや強制終了時のエラーコードの原因特定までは対処できない可能性が高いです (まだまだ本体由来のバグが多いです). 主にテキストが間違ってる, 正常に表示されない箇所があるといった問題の対応になります.
* フォントサイズはわずかに小さく調整しましたが, もしかすると文字がUIの枠からはみ出て操作しづらい箇所が発生するかもしれません. これも発見されましたら報告していただけると助かります.
* 私 (このmodの作者) はM&B2をEAの比較的早い段階で購入し, その時点で日本語対応が計画されているとアナウンスされていたので日本語化コミュニティには参加していませんでした. 日本語化された安定版が出たと聞いて久々に再開したらあんまり出来がよくなかったのでこれを作りました. そちらのものは確認してないので翻訳の方針が違うかもしれません.
* 戦闘中のログは文字の下側がやや被っています. これは調整が面倒だったので現状そのままにしています.
* 既に TaleWorlds のフォーラムで日本語ローカライズの問題について開発元に指摘してくださっている方がいます. QAチームが反応しているので, 時間がかかるかもしれませんがバニラにおける問題もそのうち修正されるかもしれません. ~~正直私は自分の作ったこの膨大な変更リストを説明する気になれません. ぶっちゃけ丸パクリされても怒らないのでさり気なく修正してほしいです~~

https://forums.taleworlds.com/index.php?threads/some-japanese-fonts-are-still-missing.454493/

## CREDIT & ACKNOWLEDGEMENT

* 源真ゴシックP は http://jikasei.me/font/genshin/ で SIL OFL 1.1 ライセンスで配布されているものを使用しました.
* 源暎ラテミンP は https://okoneya.jp/font/genei-latin.html で SIL OFL 1.1 ライセンスで配布されているものを使用しました.
* [HarmonyFont](https://www.nexusmods.com/mountandblade2bannerlord/mods/4144) の作者に FontAtlas.exe の使い方のヒントを教えてもらいました.

----------

## Summary

1. This mod corrects mojibakes which appear many times in Japanese language.
1. This mod corrects many of mistranslated text in Japanese language. Currently (v0.9) this mod corrects about 21 % of all of the original text which has 20 thousands entries

## How to Install

Currently M&B localization system is quite limited. I published two types of mod: the formal module type and overwriting type. The latter is effective to apply to the multiplayer mode.

1. As usual, download one of the Correct Localization JP-* in the Main Files, unzip, drag and drop into the Modules folder. Then enable this mod on the launcher and start to play.
2. Enter the options and select the GamePlay, and change the Language to "正しい日本語" (correct Japanese)

* Each variant is equivalent except the Japanese font
* Note that modding disables to unlock the achievements. I recommend using [AchievementUn(bloc)ker](https://www.nexusmods.com/mountandblade2bannerlord/mods/4587)
* Otherwise you can overwrite the vanilla modules by overwriter versions in the Optional Files.

## About Font Correction

Currently You can find many text with mojibake because M&B2 (v1.0.3) supports only few Japanese letters (maybe the Joyo Kanji charset). I offer the following new font options.

1. Gen-Shin Gothic Proportional (源真ゴシックP)
1. Gen-Ei Latemin Proportional (源暎ラテミンP)

Each of the font family will supports almost all of letters and symbols used in typical Japanese language.

Note: I used Gen-Shin Gothic instead of Source Han Sans JP,  same as the Native because of Modding Kit's thechnical difficulty.

## About Traslation Correction

Too many to state that here.

## CREDIT & ACKNOWLEDGEMENT

* Gen-Shin Gothic Proportional is published under SIL OFL 1.1 at http://jikasei.me/font/genshin/
* Gen-Ei Latemin Proportional is published under SIL OFL 1.1 at https://okoneya.jp/font/genei-latin.html
* I got userful comments on the usage of FontAtlas.exe from the [HarmonyFont](https://www.nexusmods.com/mountandblade2bannerlord/mods/4144)'s author.
