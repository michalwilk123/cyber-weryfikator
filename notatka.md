

Flow:

Użytkownik -> chodzi na weryfikator.gov.pl/verification -> klika weryfikuj przegladarke (Zakladam że ta strona jest bezpieczna). Musi sie uwierzytelnic z aplikacja

wysylane jest browser id do /verify-browser:
body:
{
   browser_id: BROWSER_ID
}

OK -> zapisywane jest browser_id i K_1


Uzytkownik wchodzi na strone pue.gov.pl widzi kod qr

jak wygenerowac kod qr:

- wysylane jest zapytanie do weryfikator BODY: {"browser_id" BROWSER_ID}. Generowany jest klucz 
AUTH = HMAC(K_1, TTL, Nonce, url_strony)

K_2 = KDF(K_1)

- 


a) START

weryfikator.com/weryfikujPrzegladarke 

Generowany jest kod QR:
skanowanie w aplikacji mobilnej

1) Aplikacja mobilna ma dostep do id uzytkownika pobiera kod qr z fingerprintem przegladarki

Dodawany jest wiersz do tabeli VerifiedUsers
- ID użytkownika (aplikacja ma te ID) oraz fingerprint przegladarki

2) Aplikacja wysyla do weryfikatora: ID uzytkownika, fingerprint przegladarki


b) Użytkownik wejdzie na strone np. pue.gov.pl

Na stronie jest skrypt ktory tworzy maly plik html. Skrypt wysyla żądanie do weryfikatora z fingerprintem











Aplikacja mobilna (zakladam że jest bezpieczna i jest bezpiecznie autoryzowana z weryfikatorem, polaczenie weryfikator <-> aplikacja jest okej)





Zakładam że aplikacja mObywatel ma wbudowane jakies ID użytkownika w tabeli Users

Tworzona jest tabela VerifiedClients, ktora ma:
- id uzytkownika
- browser_id (może być hash, póki co zakładam w uproszczeniu że to po prostu browser id)




