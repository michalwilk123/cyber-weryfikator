import { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, SafeAreaView, ScrollView } from 'react-native';
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
const API_ENDPOINT = 'http://localhost:8081/verify-token'; // mObywatel service endpoint
const API_METHOD = 'POST';
const API_TIMEOUT_MS = 3000; // 3 second timeout
const HARDCODED_USER_ID = 'user001'; // Hardcoded user ID for authentication

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [scannedData, setScannedData] = useState<string>('');
  const [isScanning, setIsScanning] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    if (permission && !permission.granted && permission.canAskAgain) {
      requestPermission();
    }
  }, [permission]);

  const sendToApi = async (qrData: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

      const response = await fetch(API_ENDPOINT, {
        method: API_METHOD,
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': HARDCODED_USER_ID,
        },
        body: JSON.stringify({ token: qrData }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const result = await response.json();
      console.log('API Response:', result);
      // TODO: Handle API response when backend is ready
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.error('API Timeout');
      } else {
        console.error('API Error:', error);
      }
      // TODO: Handle errors when backend is ready
    }
  };

  const handleBarCodeScanned = (result: BarcodeScanningResult) => {
    if (!isScanning) return; // Prevent multiple scans

    setScannedData(result.data);
    setIsScanning(false); // Stop scanning
    setErrorMessage(''); // Clear any previous errors

    // Check if QR code has the "verification-code" prefix
    if (result.data.startsWith('verification-code')) {
      sendToApi(result.data); // Send to API only if valid
    } else {
      setErrorMessage('Nieprawidłowy kod QR. Nie można zweryfikować strony');
    }
  };

  const handleContinue = () => {
    setScannedData('');
    setErrorMessage('');
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
        <View style={styles.bottomNav}>
          <View style={styles.navItem}>
            <Text style={styles.navText}>Usługi</Text>
          </View>
          <View style={styles.navItem}>
            <Text style={styles.navText}>Przekaż</Text>
          </View>
          <View style={[styles.navItem, styles.navItemActive]}>
            <Text style={[styles.navText, styles.navTextActive]}>Sprawdź</Text>
          </View>
          <View style={styles.navItem}>
            <Text style={styles.navText}>Historia</Text>
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
      <ScrollView style={styles.contentArea}>
        {/* Scanner Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Zweryfikuj osobę za pomocą kodu QR</Text>
          <Text style={styles.cardSubtitle}>
            Pozwól zeskanować kod, aby dokonać obustronnej wymiany danych.
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
        </View>

        {/* Result Card */}
        {scannedData ? (
          <View style={styles.card}>
            {errorMessage ? (
              // Error message display
              <>
                <Text style={styles.errorTitle}>Błąd weryfikacji</Text>
                <View style={styles.errorBox}>
                  <Text style={styles.errorText}>
                    {errorMessage}
                  </Text>
                </View>
                <View style={styles.resultBox}>
                  <Text style={styles.resultLabel}>Zeskanowany kod:</Text>
                  <Text style={styles.resultText} selectable>
                    {scannedData}
                  </Text>
                </View>
              </>
            ) : (
              // Success display
              <>
                <Text style={styles.cardTitle}>Zeskanowane dane</Text>
                <View style={styles.resultBox}>
                  <Text style={styles.resultText} selectable>
                    {scannedData}
                  </Text>
                </View>
              </>
            )}
            {!isScanning && (
              <TouchableOpacity
                style={styles.continueButton}
                onPress={handleContinue}
              >
                <Text style={styles.continueButtonText}>Kontynuuj skanowanie</Text>
              </TouchableOpacity>
            )}
          </View>
        ) : (
          <View style={styles.card}>
            <Text style={styles.instructionTitle}>Jak korzystać?</Text>
            <Text style={styles.instructionText}>
              1. Skieruj kamerę na kod QR mDokumentów{'\n'}
              2. Poczekaj na automatyczne skanowanie{'\n'}
              3. Sprawdź wyniki weryfikacji
            </Text>
          </View>
        )}
      </ScrollView>

      {/* Bottom Navigation */}
      <View style={styles.bottomNav}>
        <View style={styles.navItem}>
          <Text style={styles.navText}>Usługi</Text>
        </View>
        <View style={styles.navItem}>
          <Text style={styles.navText}>Przekaż</Text>
        </View>
        <View style={[styles.navItem, styles.navItemActive]}>
          <Text style={[styles.navText, styles.navTextActive]}>Sprawdź</Text>
        </View>
        <View style={styles.navItem}>
          <Text style={styles.navText}>Historia</Text>
        </View>
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
    paddingVertical: 16,
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
  },
  continueButtonText: {
    color: COLORS.WHITE,
    fontSize: 16,
    fontWeight: '600',
  },
  bottomNav: {
    flexDirection: 'row',
    backgroundColor: COLORS.WHITE,
    borderTopWidth: 1,
    borderTopColor: COLORS.BORDER_LIGHT,
    paddingVertical: 8,
    paddingBottom: 12,
  },
  navItem: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 8,
  },
  navItemActive: {
    borderTopWidth: 2,
    borderTopColor: COLORS.GOV_RED,
    marginTop: -2,
  },
  navText: {
    color: COLORS.TEXT_GRAY,
    fontSize: 12,
    marginTop: 4,
  },
  navTextActive: {
    color: COLORS.GOV_RED,
    fontWeight: '600',
  },
});
