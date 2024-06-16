#include <Wire.h>
#include <MCP23017.h>
#include "SHT2x.h"
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Arduino.h>
#include <string>
#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 32 // OLED display height, in pixels

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
// The pins for I2C are defined by the Wire-library. 
#define OLED_RESET     -1 // Reset pin # (or -1 if sharing Arduino reset pin)
#define SCREEN_ADDRESS 0x3C ///< See datasheet for Address; 0x3D for 128x64, 0x3C for 128x32
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

SHT2x sht;
char message[] = "Totalpoints: 100 Temperature: 20.0 Humidity: 50.5  ";
String temp_humid;
String screen_text;
int x, minX;

const int ldrPin = 27; // Define the pin number for the LDR

#define MCP23017_ADDR 0x20
MCP23017 mcp = MCP23017(MCP23017_ADDR);

#define NUM_LEDS 6
#define NUM_BUTTONS 6

// LED pins (connected to MCP23017 port A)
const uint8_t ledPins[NUM_LEDS] = {7, 6, 5, 4, 3, 2};
// Button pins (connected to MCP23017 port B)
const uint8_t buttonPins[NUM_BUTTONS] = {8, 10, 11, 9, 13, 12};

uint8_t tempLED = 0;
uint8_t activeLED = 0; // Currently active LED
bool gameActive = true;
uint8_t points = 0;

void setup() {
    Wire.begin();
    Serial.begin(115200);

    if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
        Serial.println(F("SSD1306 allocation failed"));
        for(;;); // Don't proceed, loop forever
    }

    Serial.println(__FILE__);
    Serial.print("SHT2x_LIB_VERSION: \t");
    Serial.println(SHT2x_LIB_VERSION);

    sht.begin();

    uint8_t stat = sht.getStatus();
    Serial.print(stat, HEX);
    Serial.println();
    mcp.init();
    mcp.portMode(MCP23017Port::A, 0);          // Port A as output (for LEDs)
    mcp.portMode(MCP23017Port::B, 0b11111111); // Port B as input (for buttons)

    mcp.writeRegister(MCP23017Register::GPIO_A, 0x00);  // Reset port A (turn off all LEDs initially)
    mcp.writeRegister(MCP23017Register::GPIO_B, 0x00);  // Reset port B

    // GPIO_B reflects the same logic as the input pins state
    mcp.writeRegister(MCP23017Register::IPOL_B, 0x00);
    // Uncomment this line to invert inputs (press a button to light an LED)
    // mcp.writeRegister(MCP23017Register::IPOL_B, 0xFF);
    display.clearDisplay();
    display.setTextSize(2);
    display.setTextColor(WHITE);
    display.setTextWrap(false);

    x = display.width();
    minX = -12 * strlen(message);  // 12 = 6 pixels/character * text size 2
    
    randomSeed(analogRead(0)); // Seed the random number generator
    flickerLEDs();
    lightRandomLED();
}

void loop() {
    temp_humid = readTemperatureAndHumidity();
    screen_text = "Totalpoints: " + String(points) + " " + temp_humid;
    while(TrafficLightRed()){
        display.clearDisplay();
        display.setCursor(x, 10);
        checkButtons();
        display.print(screen_text);
        display.display();
        x=x-1;
        if(x < minX) x= display.width();
    }
    flickerLEDs();
    temp_humid = readTemperatureAndHumidity();
    screen_text = "Totalpoints: " + String(points) + " " + temp_humid;
    while(!(TrafficLightRed())){
        display.clearDisplay();
        display.setCursor(x, 10);
        checkButtons();
        display.print(screen_text);
        display.display();
        x=x-1;
        if(x < minX) x= display.width();
    }
    lightRandomLED();
}
    

void lightRandomLED() {
    // Turn off all LEDs
    mcp.writePort(MCP23017Port::A, 0x00);
    tempLED = activeLED;
    // Select a random LED
    activeLED = random(NUM_LEDS);
    // Light up the selected LED
    while (activeLED == tempLED){
        activeLED = random(NUM_LEDS);
    }
    mcp.digitalWrite(ledPins[activeLED], HIGH);
    
    Serial.print("LED ");
    Serial.print(activeLED);
    Serial.println(" is lit. Press the corresponding button!");
}


void checkButtons() {
    for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
        if (activeLED == 1){
            Serial.println("Skipped!");
            delay(50); // Short delay before lighting the next LED
            lightRandomLED(); // Light up a new random LED
        }
        if (mcp.digitalRead(buttonPins[i]) == LOW) {
            if (i == activeLED) {
                Serial.println("Correct button pressed!");
                delay(50); // Short delay before lighting the next LED
                lightRandomLED(); // Light up a new random LED
                points++;
            } else {
                Serial.println("Wrong button pressed. Game Over!");
                Serial.println(i);
                // Turn off all LEDs to indicate game over
                mcp.writePort(MCP23017Port::A, 0x00);
                delay(50);
                lightRandomLED(); // Light up a new random LED
            }
            while (mcp.digitalRead(buttonPins[i]) == LOW); // Wait for button release
        }
    }
}

void flickerLEDs() {
    for (int i = 0; i < 10; i++) { // Flicker 10 times
        mcp.writePort(MCP23017Port::A, 0xFF); // Turn on all LEDs
        delay(300); // Wait 100 milliseconds
        mcp.writePort(MCP23017Port::A, 0x00); // Turn off all LEDs
        delay(300); // Wait 100 milliseconds
    }
    Serial.println("Flicker completed!");
}

void displayText(String text) {
    display.clearDisplay();

    display.setTextSize(2); // Draw 2X-scale text
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(x, 10);
    display.println((text));
    display.display();      // Show initial text
    delay(100);
    x=x-1; // scroll speed, make more positive to slow down the scroll
    if(x < minX) x= display.width();
    // Scroll in various directions, pausing in-between:
    display.startscrollright(0x00, 0x0F);
}

// Function to check if the LDR value is higher than 10
bool TrafficLightRed() {
  int ldrValue = analogRead(ldrPin); // Read the LDR value
  return ldrValue > 6; // Return true if the LDR value is higher than 10
}


String readTemperatureAndHumidity() {
  sht.read();
  float temperature = sht.getTemperature();
  float humidity = sht.getHumidity();
  String result = "Temperature: " + String(temperature, 1) + " Humidity: " + String(humidity, 1)+" ";
  return result;
}

