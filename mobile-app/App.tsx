import { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, SafeAreaView, ScrollView, Platform, StatusBar as NativeStatusBar } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { CameraView, useCameraPermissions, BarcodeScanningResult } from 'expo-camera';

// mObywatel color scheme
const COLORS = {
  GOV_RED: '#b71c2d',
  BG_GRAY: '#f5f5f5',
  TEXT_DARK: '#333333',
  WHITE: '#ffffff',
  BORDER_LIGHT: '#e0e0e0',
  TEXT_GRAY: '#666666',
};

// API Configuration
const API_ENDPOINT = 'https://mobyw-hacknation.micwilk.com/verify-token'; // mObywatel service endpoint
const API_METHOD = 'POST';
const API_TIMEOUT_MS = 3000; // 3 second timeout
const HARDCODED_USER_ID = 'user001'; // Hardcoded user ID for authentication

type VerificationStatus = 'idle' | 'success' | 'failed' | 'info';

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [scannedData, setScannedData] = useState<string>('');
  const [isScanning, setIsScanning] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatus>('idle');
  const [verifiedDomain, setVerifiedDomain] = useState<string>('');

  useEffect(() => {
    if (permission && !permission.granted && permission.canAskAgain) {
      requestPermission();
    }
  }, [permission]);

  const sendToApi = async (qrData: string) => {
    console.log('=== API Request Starting ===');
    console.log('QR Data:', qrData);
    console.log('Endpoint:', API_ENDPOINT);
    console.log('Method:', API_METHOD);
    console.log('User ID:', HARDCODED_USER_ID);
    console.log('Timeout:', API_TIMEOUT_MS, 'ms');
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

      const requestBody = { token: qrData };
      console.log('Request Body:', JSON.stringify(requestBody));

      console.log('Sending fetch request...');
      const response = await fetch(API_ENDPOINT, {
        method: API_METHOD,
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': HARDCODED_USER_ID,
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      
      console.log('Response Status:', response.status);
      console.log('Response Status Text:', response.statusText);
      console.log('Response OK:', response.ok);
      console.log('Response Headers:', JSON.stringify(Object.fromEntries(response.headers.entries())));
      
      const responseText = await response.text();
      console.log('Response Text:', responseText);
      
      let result;
      try {
        result = JSON.parse(responseText);
        console.log('Parsed Response:', result);
      } catch (parseError) {
        console.error('Failed to parse response as JSON:', parseError);
        console.log('Raw response text:', responseText);
        setVerificationStatus('failed');
        setErrorMessage('Błąd parsowania odpowiedzi serwera');
        return;
      }
      
      if (!response.ok) {
        console.log('Response not OK. Status:', response.status);
        if (response.status === 401) {
             setVerificationStatus('failed');
             // setErrorMessage is kept empty or descriptive to avoid showing "Server Error" in UI if that's what was happening
             setErrorMessage(''); 
             return;
        }

        setVerificationStatus('failed');
        setErrorMessage('Błąd serwera');
        return;
      }
      
      console.log('=== API Request Successful ===');
      
      // Handle API response
      if (result.valid === true) {
        setVerificationStatus('success');
        setVerifiedDomain(result.domain || '');
        setErrorMessage('');
      } else {
        setVerificationStatus('failed');
        setErrorMessage(result.message || 'Weryfikacja nie powiodła się');
      }
    } catch (error: any) {
      console.error('=== API Request Failed ===');
      
      if (error.name === 'AbortError') {
        console.error('Error Type: Timeout');
        console.error('The request timed out after', API_TIMEOUT_MS, 'ms');
        setVerificationStatus('failed');
        setErrorMessage('Przekroczono czas oczekiwania');
      } else if (error.name === 'TypeError') {
        console.error('Error Type: Network/CORS Error');
        console.error('Possible causes:');
        console.error('- Network connection issue');
        console.error('- CORS policy blocking the request');
        console.error('- Invalid URL or server not reachable');
        setVerificationStatus('failed');
        setErrorMessage('Błąd połączenia sieciowego');
      } else {
        console.error('Error Type:', error.name);
        setVerificationStatus('failed');
        setErrorMessage('Nieznany błąd weryfikacji');
      }
      
      console.error('Error Message:', error.message);
      console.error('Error Object:', error);
      console.error('Error Stack:', error.stack);
    }
  };

  const handleBarCodeScanned = (result: BarcodeScanningResult) => {
    if (!isScanning) return; // Prevent multiple scans

    setScannedData(result.data);
    setIsScanning(false); // Stop scanning
    setErrorMessage(''); // Clear any previous errors

    // Check if QR code has the "verification-code" prefix
    if (result.data.startsWith('verification-code:')) {
      // Extract the base64 token part (after the prefix)
      const token = result.data.replace('verification-code:', '');
      sendToApi(token); 
    } else if (result.data.startsWith('verification-code')) {
        // Handle case where colon might be missing or different format
        // This is a fallback/robustness check
         const token = result.data.replace('verification-code', '');
         sendToApi(token);
    } else {
      // No verification prefix - show info message
      setVerificationStatus('info');
      setErrorMessage('Zeskanuj kod walidacyjny');
    }
  };

  const handleContinue = () => {
    setScannedData('');
    setErrorMessage('');
    setVerificationStatus('idle');
    setVerifiedDomain('');
    setIsScanning(true); // Resume scanning
  };

  if (!permission) {
    // Camera permissions are still loading
    return (
      <SafeAreaView style={styles.safeArea}>
        <StatusBar style="light" />
        <View style={styles.header}>
          <Text style={styles.headerTitle}>CyberWeryfikator</Text>
        </View>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Ładowanie...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!permission.granted) {
    // Camera permissions are not granted
    return (
      <SafeAreaView style={styles.safeArea}>
        <StatusBar style="light" />
        <View style={styles.header}>
          <Text style={styles.headerTitle}>CyberWeryfikator</Text>
        </View>
        <View style={styles.contentArea}>
          <View style={styles.permissionCard}>
            <Text style={styles.permissionTitle}>Dostęp do kamery</Text>
            <Text style={styles.permissionMessage}>
              Aby skanować kody QR, aplikacja potrzebuje dostępu do kamery.
            </Text>
            <TouchableOpacity 
              style={styles.permissionButton} 
              onPress={requestPermission}
            >
              <Text style={styles.permissionButtonText}>Zezwól na dostęp</Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>CyberWeryfikator</Text>
      </View>

      {/* Main Content */}
      <View style={styles.contentArea}>
        {!scannedData ? (
          /* Scanner Card */
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Weryfikacja strony rządowej</Text>
            <Text style={styles.cardSubtitle}>
              Zeskanuj kod QR ze strony gov.pl, aby potwierdzić jej autentyczność.
            </Text>
            <View style={styles.cameraContainer}>
              <CameraView
                style={styles.camera}
                facing="back"
                barcodeScannerSettings={{
                  barcodeTypes: ['qr'],
                }}
                onBarcodeScanned={isScanning ? handleBarCodeScanned : undefined}
              />
            </View>
            <View style={styles.instructionContainer}>
              <Text style={styles.instructionTitle}>Jak to działa?</Text>
              <Text style={styles.instructionText}>
                1. Znajdź kod QR na stronie internetowej{'\n'}
                2. Zeskanuj go tą aplikacją{'\n'}
                3. Otrzymasz potwierdzenie, czy strona jest bezpieczna
              </Text>
            </View>
          </View>
        ) : (
          /* Result Card */
          <ScrollView style={styles.scrollContainer}>
            <View style={styles.card}>
              {verificationStatus === 'success' ? (
                // Success Screen (Green)
                <View style={styles.successScreen}>
                  <Text style={styles.successTitle}>✓ Strona zweryfikowana</Text>
                  
                  <View style={styles.verificationBadge}>
                    <Text style={styles.badgeText}>DOSTĘP DO USŁUG PUBLICZNYCH</Text>
                  </View>

                  <Text style={styles.domainLabel}>Zweryfikowana domena:</Text>
                  <Text style={styles.domainText}>{verifiedDomain}</Text>
                  
                  {verifiedDomain.endsWith('.gov.pl') && (
                    <View style={styles.secureBadge}>
                      <Text style={styles.secureBadgeText}>✓ Domena rządowa .gov.pl</Text>
                    </View>
                  )}
                  
                  <View style={styles.securityInfo}>
                    <Text style={styles.securityText}>🔒 Połączenie szyfrowane (SSL)</Text>
                    <Text style={styles.securityText}>🛡️ Certyfikat ważny</Text>
                  </View>

                  <Text style={styles.successInstructions}>
                    Możesz bezpiecznie korzystać z tej strony. Weryfikacja potwierdza autentyczność serwisu.
                  </Text>
                  
                  <View style={styles.infoLink}>
                     <Text style={styles.infoLinkText}>Zobacz listę oficjalnych portali gov.pl</Text>
                  </View>
                </View>
              ) : verificationStatus === 'failed' ? (
                // Failed Screen (Red)
                <View style={styles.failedScreen}>
                  <Text style={styles.failedTitle}>⚠️ OSTRZEŻENIE</Text>
                  <Text style={styles.failedWarning}>
                    Strona NIE jest autentyczna!
                  </Text>
                  
                  <View style={styles.dangerBadge}>
                    <Text style={styles.badgeText}>PODEJRZENIE PHISHIGU</Text>
                  </View>

                  <Text style={styles.failedInstructions}>
                    Wykryto potencjalną próbę oszustwa.{'\n'}
                    Strona może podszywać się pod serwis rządowy.
                  </Text>

                  <View style={styles.actionList}>
                    <Text style={styles.actionItem}>⛔ Nie podawaj żadnych danych</Text>
                    <Text style={styles.actionItem}>❌ Natychmiast opuść stronę</Text>
                    <Text style={styles.actionItem}>📢 Zgłoś incydent do CERT Polska</Text>
                  </View>
                </View>
              ) : verificationStatus === 'info' ? (
                // Info Screen (Neutral)
                <View style={styles.infoScreen}>
                  <Text style={styles.infoTitle}>ℹ️ Nieznany kod</Text>
                  <Text style={styles.infoMessage}>
                    Zeskanowany kod nie pochodzi z systemu weryfikacji stron rządowych.
                  </Text>
                </View>
              ) : (
                // Default display (when verification is in progress)
                <View style={styles.loadingResult}>
                  <Text style={styles.cardTitle}>Weryfikacja...</Text>
                  <Text style={styles.loadingText}>Sprawdzanie certyfikatu i domeny</Text>
                </View>
              )}
              
              <TouchableOpacity
                style={styles.continueButton}
                onPress={handleContinue}
              >
                <Text style={styles.continueButtonText}>Skanuj ponownie</Text>
              </TouchableOpacity>
            </View>
          </ScrollView>
        )}
      </View>

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: COLORS.GOV_RED,
  },
  header: {
    backgroundColor: COLORS.GOV_RED,
    paddingTop: 45,
    paddingBottom: 16,
    paddingHorizontal: 20,
    alignItems: 'center',
  },
  headerTitle: {
    color: COLORS.WHITE,
    fontSize: 20,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  contentArea: {
    flex: 1,
    backgroundColor: COLORS.BG_GRAY,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: COLORS.BG_GRAY,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: COLORS.TEXT_DARK,
    fontSize: 16,
  },
  card: {
    backgroundColor: COLORS.WHITE,
    marginHorizontal: 16,
    marginTop: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    color: COLORS.TEXT_DARK,
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
  cardSubtitle: {
    color: COLORS.TEXT_GRAY,
    fontSize: 14,
    marginBottom: 16,
    lineHeight: 20,
  },
  cameraContainer: {
    height: 300,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: '#000',
  },
  camera: {
    flex: 1,
  },
  resultBox: {
    backgroundColor: COLORS.BG_GRAY,
    borderRadius: 8,
    padding: 16,
    marginTop: 12,
    borderWidth: 1,
    borderColor: COLORS.BORDER_LIGHT,
  },
  resultLabel: {
    color: COLORS.TEXT_GRAY,
    fontSize: 12,
    marginBottom: 8,
    fontWeight: '600',
  },
  resultText: {
    color: COLORS.TEXT_DARK,
    fontSize: 14,
    lineHeight: 22,
  },
  // Success Screen Styles
  successScreen: {
    backgroundColor: '#2e7d32',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
  },
  successTitle: {
    color: COLORS.WHITE,
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 20,
  },
  successNote: {
    color: COLORS.WHITE,
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 8,
    opacity: 0.95,
  },
  domainText: {
    color: COLORS.WHITE,
    fontSize: 32,
    fontWeight: '800',
    textAlign: 'center',
    marginBottom: 20,
    letterSpacing: 1,
  },
  successInstructions: {
    color: COLORS.WHITE,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 16,
    lineHeight: 20,
    opacity: 0.95,
  },
  // Failed Screen Styles
  failedScreen: {
    backgroundColor: COLORS.GOV_RED,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
  },
  failedTitle: {
    color: COLORS.WHITE,
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 12,
  },
  failedWarning: {
    color: COLORS.WHITE,
    fontSize: 20,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 16,
  },
  failedMessage: {
    color: COLORS.WHITE,
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
    opacity: 0.9,
  },
  failedInstructions: {
    color: COLORS.WHITE,
    fontSize: 14,
    textAlign: 'left',
    marginBottom: 16,
    lineHeight: 22,
    opacity: 0.95,
  },
  // Info Screen Styles
  infoScreen: {
    backgroundColor: '#ff9800',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
  },
  infoTitle: {
    color: COLORS.WHITE,
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 12,
  },
  infoMessage: {
    color: COLORS.WHITE,
    fontSize: 15,
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 22,
    opacity: 0.95,
  },
  // Token Preview Styles (small, collapsed)
  tokenPreview: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 8,
    padding: 12,
    width: '100%',
    marginTop: 8,
  },
  tokenPreviewLabel: {
    color: COLORS.WHITE,
    fontSize: 11,
    fontWeight: '600',
    marginBottom: 4,
    opacity: 0.9,
  },
  tokenPreviewText: {
    color: COLORS.WHITE,
    fontSize: 10,
    opacity: 0.8,
    fontFamily: 'monospace',
  },
  errorTitle: {
    color: COLORS.GOV_RED,
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
  errorBox: {
    backgroundColor: '#ffebee',
    borderRadius: 8,
    padding: 16,
    marginTop: 12,
    borderWidth: 1,
    borderColor: '#ffcdd2',
  },
  errorText: {
    color: COLORS.GOV_RED,
    fontSize: 14,
    lineHeight: 22,
    fontWeight: '600',
  },
  instructionTitle: {
    color: COLORS.TEXT_DARK,
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  instructionText: {
    color: COLORS.TEXT_GRAY,
    fontSize: 14,
    lineHeight: 24,
  },
  permissionCard: {
    backgroundColor: COLORS.WHITE,
    marginHorizontal: 16,
    marginTop: 40,
    padding: 24,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  permissionTitle: {
    color: COLORS.TEXT_DARK,
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 12,
    textAlign: 'center',
  },
  permissionMessage: {
    color: COLORS.TEXT_GRAY,
    fontSize: 15,
    lineHeight: 22,
    textAlign: 'center',
    marginBottom: 24,
  },
  permissionButton: {
    backgroundColor: COLORS.GOV_RED,
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
  },
  permissionButtonText: {
    color: COLORS.WHITE,
    fontSize: 16,
    fontWeight: '600',
  },
  continueButton: {
    marginTop: 16,
    backgroundColor: COLORS.GOV_RED,
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
    width: '100%',
  },
  continueButtonText: {
    color: COLORS.WHITE,
    fontSize: 16,
    fontWeight: '600',
  },
  scrollContainer: {
    flex: 1,
  },
  instructionContainer: {
    marginTop: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: COLORS.BORDER_LIGHT,
  },
  verificationBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.4)',
  },
  badgeText: {
    color: COLORS.WHITE,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  domainLabel: {
    color: COLORS.WHITE,
    fontSize: 14,
    opacity: 0.9,
    marginBottom: 4,
  },
  secureBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    marginBottom: 20,
  },
  secureBadgeText: {
    color: COLORS.WHITE,
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  securityInfo: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    width: '100%',
    marginBottom: 24,
    backgroundColor: 'rgba(0, 0, 0, 0.1)',
    padding: 12,
    borderRadius: 8,
  },
  securityText: {
    color: COLORS.WHITE,
    fontSize: 12,
    fontWeight: '500',
  },
  infoLink: {
    marginTop: 16,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.WHITE,
  },
  infoLinkText: {
    color: COLORS.WHITE,
    fontSize: 14,
    fontWeight: '500',
    paddingBottom: 2,
  },
  dangerBadge: {
    backgroundColor: '#d32f2f',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.4)',
  },
  actionList: {
    width: '100%',
    backgroundColor: 'rgba(0, 0, 0, 0.1)',
    borderRadius: 8,
    padding: 16,
    marginTop: 16,
  },
  actionItem: {
    color: COLORS.WHITE,
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  loadingResult: {
    alignItems: 'center',
    padding: 20,
  },
});
