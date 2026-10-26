# Line Coach — tekstipohjainen ajolinjatutkimus (0.3.0 research)

## Tarkoitus

Ei erillistä karttaikkunaa eikä rataviivojen näyttöä ajon aikana.
Mini HUDin tavoite on edelleen **yksi numero + yksi lyhyt tekstipalaute**.
Tässä paketissa Line Coach toimii vasta erillisenä, vapaaehtoisena
**vain lukevana mittausprototyyppinä**. Se ei muuta Mini HUDin, jarrutusarvosanojen
ja palautteen ajoitusta, eikä lisää ajolinjatekstejä varsinaiseen HUDiin vielä.

## Mikä on oikeasti varmistettu?

- Käyttäjän ACC Nürburgring 24h `fastlane.ai` on ACC v8 -formaattia; sen
  ensimmäisestä pisteblokista saadaan 5 046 kolmiulotteista pistettä.
- `line_reference.py` lukee pisteet paikallisesti suoraan ACC:n omasta tiedostosta,
  tarkistaa version ja pistejärjestyksen sekä laskee sivuttaispoikkeaman lähimpään
  reittisegmenttiin (metreinä). Vain X/Z-kenttää käytetään sivuttaismittaan;
  korkeuseroa käytetään päällekkäisten ratakohtien erotteluun.
- `acc_graphics_probe.py` lukee `Local\acpmf_graphics`-muistialuetta Windowsin
  `OpenFileMappingW(FILE_MAP_READ)`-kutsulla ja hakee oikean auton `playerCarID`-
  tunnisteella, EI sijalla 0.
- Grafiikkamuistin kenttien todellista yhteensopivuutta käyttäjän ACC-asennuksessa
  ei ole vielä testattu. Jos tiedot eivät täsmää, mitään ajolinjan arvosanaa ei anneta.
- AI:n `fastlane.ai`-reittiä EI ole varmistettu samaksi kuin ACC:n vihreä opastusviiva.
  Myöskään AI-reitistä poikkeaminen ei itsessään osoita virheellistä ajoa.

## Käyttö Windowsissa (vapaaehtoinen testi)

1. Pidä toimiva Advanced Trail Braking 0.2.5.3 talteen; pura uusi paketti omaan
   kansioonsa. Älä korvaa vanhaa kansiota.
2. Aja ensin `install_windows.bat` (asentaa paketissa olevan oman `.venv`-ympäristön)
   ja `run_line_probe_preflight.bat` ACC:n ollessa suljettuna.
3. Käynnistä ACC normaalisti ja mene Nürburgring 24h -radalle harjoittelutilaan.
4. Vedä ACC:n omasta asennuskansiosta löytyvä `fastlane.ai` hiirellä
   `run_line_probe_live.bat`-tiedoston päälle. Vaihtoehtoisesti kutsu BAT-tiedostoa
   polun kanssa: `run_line_probe_live.bat "D:\...\fastlane.ai"`.
5. Hyväksy käynnistys. Ohjelma tarkkailee korkeintaan 90 sekuntia. Aja rauhallisesti
   ehjällä autolla; varikkosuoralla tai mutkassa riittää lyhyt pätkä.
6. `data/line_probe_YYYYMMDD_HHMMSS.csv` sisältää ajan, auton XYZ-koordinaatit,
   AI-reitin etäisyyden, puolen ja tarkistustiedot. Lähetä vain tämä CSV, jos haluat
   että tarkistan koordinaattien vastaavuuden ja poikkeamalukemien uskottavuuden.

Voit myös kokeilla pelkkää tiedostonlukua ilman peliä:

`\.venv\Scripts\python.exe line_probe_text.py --fastlane "D:\...\fastlane.ai"`

Tämä tutkimustyökalu **ei** käynnistä peliä, kosketa ohjaimeen, kirjoita ACC:n
muistiin, lähetä tietoa verkkoon tai julkaise mitään GitHubiin. Mitään rekisteri-
tai järjestelmämuutoksia ei tarvita. Ajojen paikallinen CSV on `.gitignore`-suojattu.

## Seuraava hyväksyntäraja

Vasta, kun samalla Windows-koneella saamme riittävän pitkiä, johdonmukaisia
koordinaattisarjoja oikealta radalta ja voimme mitata poikkeaman luotettavasti,
liitämme Line Coachin Mini HUDiin. Silloinkin palaute pysyy lyhyenä, esimerkiksi
`Near AI reference`, `1.5 m right of AI line` tai `Line data unavailable`.

Ilmaisuja kuten `Missed apex`, `Wrong racing line` ja `Perfect exit` ei tehdä
vain poikkeamaetäisyydestä — ne vaativat mutkan sijainnin, vertailun ja tuloksen
validoinnin. Nykyistä toimivaa palautteen rytmiä ei muuteta.
