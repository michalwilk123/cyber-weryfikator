Dokumentacja Projektowa: Moduł Weryfikacji Autentyczności Stron


## 1. Zakres realizacji


Zrealizowano prototyp systemu weryfikacji autentyczności stron administracji publicznej. Rozwiązanie to polega na tworzeniu mechanizmu

a) componentu w tagu <script> który generuje kod QR .Typowy mechanizm wielu aplikacji webowych

b) serwisu API weryfikator który odpowiada za tworzenie i weryfikacje sekretow.

c) prostej aplikacji / komponentu w frameworku react native która umożliwa wykrywanie kodów QR. Docelowo łatwo wdrażalnej do aplikacji mObywatel


. Stworzono pełną symulację całej infrastruktury aby lepiej zoobrazować mechanizm weryfikacji stron:

    przykładowa aplikacje banku: bank.pl która byłaby tym przykładowym serwisem który chcemy werifikować
    przykładowa część backendu aplikacji mObywatel


API Weryfikator jak to często bywa z systemami które w organizacjach odpowiadaja za tworzenie i zarządzanie sekretami jak na przykład hashicorp/vault, jest odłączona od ruchu publicznego i jest dostępna tylko w sieci wewnętrznej


W tym celu stworzono sieć docker compose która składa sie z 3 kontenerow


Ponadto całą aplikacje wdrożono na serwer publiczny za pomocą platformy Dokploy i stworzono domeny dla każdego z 2 udostępnionych serwisów. Wszystkie serwisy sa szyfrowane protokołem TLS (https) i chronione przez serwis cloudflare


**Zaimplementowane funkcje:**


- Generowanie tokenów weryfikacyjnych zabezpieczonych HMAC-SHA256

- Walidacja tokenów przez aplikację mobilną

- Skanowanie kodów QR aparatem urządzenia

- Wyświetlanie statusu weryfikacji (pozytywny/negatywny/nierozpoznany)

- Kontrola certyfikatów SSL i nagłówków bezpieczeństwa

- Mechanizm częstego (póki co 10 s) odświeżania tokenów w tle

-	weryfikacja domeny pod względem większości typowych przypadków ze strony badssl.com

-	weryfikacja czy domena znajduje się na whiteliście akceptowanych domen

    weryfikacja czy domena ma oficjalny certyfikat strony rządowej gov.pl


## 2. Architektura techniczna


**Backend (Python/FastAPI):**

- Framework: FastAPI

- Kryptografia: HMAC-SHA256 (tworzenie weryfikacja kluczy), pyOpenSSL

- Funkcje: generowanie tokenów, weryfikacja certyfikatów, walidacja nagłówków HTTP


**Aplikacja mobilna (React Native/Expo):**

- Platforma: React Native z Expo

- Skaner: natywny komponent skanera QR

- Komunikacja: HTTP REST API

- Autoryzacja: nagłówek X-User-ID


**Integracja strony:**

- Worker w tle pobierający tokeny

- Zapis tokenu do pliku statycznego (secret.txt) Podobnie jak algorytm ACME

- JavaScript generujący kod QR na podstawie pliku


**Protokół weryfikacji:**

1. Strona rządowa pobiera token z serwera weryfikującego

2. Token zapisywany do pliku tekstowego

3. Frontend generuje kod QR z tokenu za pomoca komponentu

4. Aplikacja mobilna skanuje kod

5. Aplikacja wysyła token do walidacji

6. Serwer zwraca status weryfikacji


## 3. Decyzje implementacyjne


**Weryfikacja certyfikatów (pyOpenSSL):**

- Zastosowano bibliotekę pyOpenSSL do analizy łańcucha certyfikatów

- System weryfikuje wystawcę certyfikatu (Certum Trusted Network CA)

- Odrzucane są certyfikaty wystawione przez nieuznane CA


**Dystrybucja tokenów (integracja plikowa):**

- Token zapisywany do pliku tekstowego na serwerze

- Frontend odczytuje plik i generuje kod QR

- Model zbliżony do weryfikacji własności domeny (ACME, Google Search Console)


**Format tokenów (stateless):**

- Tokeny zawierają timestamp i losową wartość

- Podpis HMAC zapewnia integralność

-	tokeny mają zintegrowany secret, pepper, salt domene przegladarki, ttl i timestamp

- Brak przechowywania historii tokenów w bazie danych

- Krótki czas ważności (TTL)


**Pokrycie testami:**

- Testy jednostkowe dla aplikacji mobilnej

- Testy integracyjne weryfikacji

-	status testow mozna zobaczyc poprzez serwis github bo podstawowe github actions z testami zostało również zaimplementowane




