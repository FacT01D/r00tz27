/*
 It's a memory game! Start the game by pressing one of the buttons. When a button lights up, 
 press the button, repeating the sequence. The sequence will get longer and longer. The game is won after 
 10 rounds.

 Generates random sequence, plays music, and displays button lights.
 */
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

Adafruit_SSD1306 display = Adafruit_SSD1306(128, 32, &Wire);

#define CHOICE_OFF      0 //Used to control LEDs
#define CHOICE_NONE     0 //Used to check buttons

// Define choice variables for different LEDs/options
#define CHOICE_GREEN    16
#define CHOICE_RED      8
#define CHOICE_YELLOW   4
#define CHOICE_BLUE     2

// Variable to define the number of LEDs being used
#define NO_OF_LEDS  4

// Pin numbers corresponding to each LED
#define LED_GREEN   26
#define LED_RED     25
#define LED_YELLOW  4
#define LED_BLUE    21

// Pin numbers corresponding to each Button
#define BUTTON_GREEN  32
#define BUTTON_RED    15
#define BUTTON_YELLOW 33
#define BUTTON_BLUE   27

#define BUTTON_1 27
#define BUTTON_2 33
#define BUTTON_3 15
#define BUTTON_4 32

// Buzzer pin definition
#define BUZZER  12

// Define game parameters
#define LEVELS_TO_COMPLETE      10 //Number of rounds to successfully remember before you win. 13 is do-able.
#define ENTRY_TIME_LIMIT   3500 //Amount of time to press a button before game times out. 3500ms = 3.5 sec

// Game state variables
byte gameBoard[32]; //Contains the combination of buttons as we advance
byte gameRound = 0; //Counts the number of succesful rounds the player has made it through

void setup()
{
  Serial.begin(115200);
  Serial.println("OLED FeatherWing test");
  // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C); // Address 0x3C for 128x32

  Serial.println("OLED begun");

  // Show image buffer on the display hardware.
  // Since the buffer is intialized with an Adafruit splashscreen
  // internally, this will display the splashscreen.
  display.display();
  delay(1000);

  // Clear the buffer.
  display.clearDisplay();
  display.display();

  // text display tests
  // display.setTextSize(1);
  display.setTextSize(3);
  display.setTextColor(WHITE);
  display.setCursor(0,0);
  display.print("Roar!");
 // display.print("rocks!");
  //display.println("IP: 10.0.1.23");
  //display.println("Sending val #0");
  display.setCursor(0,0);
  display.display(); // actually display all of the above
  
  // Enable pull ups on inputs
  pinMode(BUTTON_RED, INPUT_PULLUP);
  pinMode(BUTTON_GREEN, INPUT_PULLUP);
  pinMode(BUTTON_YELLOW, INPUT_PULLUP);
  pinMode(BUTTON_BLUE, INPUT_PULLUP);

  // Set up LED pin numbers as output 
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  
  //button 1,2,3,4
  pinMode(27, INPUT_PULLUP);
  pinMode(33, INPUT_PULLUP);
  pinMode(15, INPUT_PULLUP);
  pinMode(32, INPUT_PULLUP);

  // Set up the Buzzer as another output since we will be emitting sound tones
  pinMode(BUZZER, OUTPUT);

  // Good way to check if we have set everything up correctly
  play_winner(); 
}

void loop()
{  
  bool bRet = false;
  byte button = 0;
  
  display.clearDisplay();
  display.display();
  display.print("Roar!");
  display.setCursor(0,0);
  display.display();
  // Indicate the start of game play by turning ON all LEDs and then turning them OFF
  setLEDs(CHOICE_BLUE | CHOICE_YELLOW | CHOICE_RED | CHOICE_GREEN);
  delay(1000);
  setLEDs(CHOICE_OFF); // Turn off LEDs
  delay(250);

  while( true )
  { 
    button = wait_for_button();
    if( button != 0 )
    {
      break;
    }
  }
  delay(1000);
  // Play memory game and handle result
  bRet = play_memory();
  if (bRet == true) 
    play_winner(); // Player won, play winner tones
  else 
    play_loser(); // Player lost, play loser tones

  display.clearDisplay();
  display.print( "Game Over" );
  display.setCursor(0,0);
  display.display();
  delay(1000);
}

// Play the regular memory game
// Returns 0 if player loses, or 1 if player wins

boolean play_memory(void)
{
  int c = 0;
  // This is to ensure we get a close to perfect random number generator
  randomSeed(analogRead(0)); // Seed the random generator with random analog value read from pin 0

  gameRound = 0; // Reset the game to the beginning

  // Should only execute if there are incomplete levels
 
  while (gameRound < LEVELS_TO_COMPLETE)
  {
    
    add_to_moves(); // Add a button to the current moves, then play them back

    playMoves(); // Play back the current game board

    // Then require the player to repeat the sequence.
    
    for (byte currentMove = 0 ; currentMove < gameRound ; currentMove++)
    {
      byte choice = wait_for_button(); // See what button the user presses
      if (choice == 0) {
      
      while (c < 3) {
        
        c++;
        if (c >= 3){return false;}
      }
      return false; // If wait timed out, player loses
      }
      if (choice != gameBoard[currentMove]) return false; // If the choice is incorrect, player loses
    }
    delay(1000); // Player was correct, delay before play continues
  }
  return true; // Player made it through all the rounds to win!
}

/*
boolean play_memory(void)
{
  // This is to ensure we get a close to perfect random number generator
  randomSeed(analogRead(0)); // Seed the random generator with random analog value read from pin 0

  gameRound = 0; // Reset the game to the beginning

  // Should only execute if there are incomplete levels
  while (gameRound < LEVELS_TO_COMPLETE) 
  {
    add_to_moves(); // Add a button to the current moves, then play them back

    playMoves(); // Play back the current game board

    // Then require the player to repeat the sequence.
    for (byte currentMove = 0 ; currentMove < gameRound ; currentMove++)
    {
      byte choice = wait_for_button(); // See what button the user presses
      if (choice == 0) return false; // If wait timed out, player loses
      if (choice != gameBoard[currentMove]) return false; // If the choice is incorrect, player loses
    }
    delay(1000); // Player was correct, delay before play continues
  }
  return true; // Player made it through all the rounds to win!
}
*/
// Plays the current contents of the game moves
// i.e. plays the current sequence of LED tones
void playMoves(void)
{
  for (byte currentMove = 0 ; currentMove < gameRound ; currentMove++) 
  {
    toner(gameBoard[currentMove], 150);

    // Wait some amount of time between button playback
    delay(150);
  }
}

// Adds a new random button to the game sequence, by sampling the timer i.e. levelling up
void add_to_moves(void)
{
  byte newButton = random(0, NO_OF_LEDS); //min (included), max (exluded)

  // We have to convert this number, 0 to NO_OF_LEDS - 1, to CHOICEs
  // Include a new choice here if an extra LED is added
  if(newButton == 0) newButton = CHOICE_BLUE;
  else if(newButton == 1) newButton = CHOICE_YELLOW;
  else if(newButton == 2) newButton = CHOICE_RED;
  else if(newButton == 3) newButton = CHOICE_GREEN;

  gameBoard[gameRound++] = newButton; // Add this new button to the game array
}

// Lights a given LEDs
// This function will display the sequence through LEDs
// Pass in a byte that is made up from CHOICE_RED, CHOICE_YELLOW, etc
void setLEDs(byte leds)
{
  if ((leds & CHOICE_BLUE) != 0)
    digitalWrite(LED_BLUE, HIGH);
  else
    digitalWrite(LED_BLUE, LOW);
  
  if ((leds & CHOICE_RED) != 0)
    digitalWrite(LED_RED, HIGH);
  else
    digitalWrite(LED_RED, LOW);

  if ((leds & CHOICE_GREEN) != 0)
    digitalWrite(LED_GREEN, HIGH);
  else
    digitalWrite(LED_GREEN, LOW);

  if ((leds & CHOICE_YELLOW) != 0)
    digitalWrite(LED_YELLOW, HIGH);
  else
    digitalWrite(LED_YELLOW, LOW);
}

// Wait for a button to be pressed. 
// Returns one of LED colors (LED_RED, etc.) if successful, 0 if timed out
byte wait_for_button(void)
{
  long startTime = millis(); // Store the time we started the loop
//Serial.println("In wait_for_button");
  while ( (millis() - startTime) < ENTRY_TIME_LIMIT) // Loop until too much time has passed
  {
    byte button = checkButton();

    if (button != CHOICE_NONE)
    { 
      toner(button, 150); // Play the button the user just pressed
      while(checkButton() != CHOICE_NONE) ;  // Now let's wait for user to release button
      delay(10); // This helps in eliminating switch bounce effects and accidental double taps
      return button;
    }
  }
  return CHOICE_NONE; // If we get here, we've timed out!
}

// Returns a '1' bit in the position corresponding to CHOICE_RED, CHOICE_GREEN, etc.
// Checks to see if a button was pressed and returns what LED it was corresponding to 
byte checkButton(void)
{
      //read the pushbutton value into a variable
  int sensorVal4 = digitalRead(27);
  int sensorVal3 = digitalRead(33);
  int sensorVal2 = digitalRead(15);
  int sensorVal1 = digitalRead(32);
  //print out the value of the pushbutton
  //Serial.println(sensorVal1);
  //Serial.println(sensorVal2);
  //Serial.println(sensorVal3);
  //Serial.println(sensorVal4);
  if (sensorVal1 == 0) return(CHOICE_BLUE); 
  else if (sensorVal2 == 0) return(CHOICE_YELLOW);
  else if (sensorVal3 == 0) return(CHOICE_RED);
  else if (sensorVal4 == 0) return(CHOICE_GREEN);

  return(CHOICE_NONE); // If no button is pressed, return none
}

// Light an LED and play tone
// Play a tone specific to each LED to aid in audio and visual cues
void toner(byte which, int buzz_length_ms)
{
  setLEDs(which); //Turn on a given LED

  //Play the sound associated with the given LED
  switch(which) 
  {
  case CHOICE_BLUE:
    buzz_sound(buzz_length_ms, 1592); 
    break;
  case CHOICE_RED:
    buzz_sound(buzz_length_ms, 1136); 
    break;
  case CHOICE_GREEN:
    buzz_sound(buzz_length_ms, 568); 
    break;
  case CHOICE_YELLOW:
    buzz_sound(buzz_length_ms, 638); 
    break;
  }
  setLEDs(CHOICE_OFF); // Turn off all LEDs
}

// Toggle buzzer every buzz_delay_us, for a duration of buzz_length_ms.
void buzz_sound(int buzz_length_ms, int buzz_delay_us)
{
  // Convert total play time from milliseconds to microseconds
  long buzz_length_us = buzz_length_ms * (long)1000;

  // Loop until the remaining play time is less than a single buzz_delay_us
  while (buzz_length_us > (buzz_delay_us * 2))
  {
    buzz_length_us -= buzz_delay_us * 2; //Decrease the remaining play time

    // Toggle the buzzer at various speeds
    digitalWrite(BUZZER, LOW);
    delayMicroseconds(buzz_delay_us);

    digitalWrite(BUZZER, HIGH);
    delayMicroseconds(buzz_delay_us);
  }
}

// Play the winner sound and lights
void play_winner(void)
{
  display.clearDisplay();
  display.display();
  display.print("You Win!");
  display.setCursor(0,0);
  display.display();
  setLEDs(CHOICE_GREEN);
  winner_sound();
  setLEDs(CHOICE_RED | CHOICE_YELLOW);
  winner_sound();
  setLEDs(CHOICE_GREEN);
  winner_sound();
  setLEDs(CHOICE_RED | CHOICE_YELLOW);
  winner_sound();
  setLEDs(CHOICE_BLUE);
  winner_sound();
}

// Play the winner sound
// This is just a unique sound, can be easily modified by changing a few parameters 
// (Try it out for yourself!)
void winner_sound(void)
{
  // Toggle the buzzer at various speeds
  for (byte x = 250 ; x > 70 ; x--)
  {
    for (byte y = 0 ; y < 3 ; y++)
    {
      digitalWrite(BUZZER, LOW);
      delayMicroseconds(x);

      digitalWrite(BUZZER, HIGH);
      delayMicroseconds(x);
    }
  }
}

// Play the loser sound/lights
void play_loser(void)
{
  display.clearDisplay();
  display.display();
  display.print("Awww!");
  display.setCursor(0,0);
  display.display();
  setLEDs(CHOICE_RED | CHOICE_GREEN);
  buzz_sound(255, 1500);
  setLEDs(CHOICE_YELLOW);
  buzz_sound(255, 1500);
  setLEDs(CHOICE_RED | CHOICE_GREEN);
  buzz_sound(255, 1500);
  setLEDs(CHOICE_YELLOW);
  buzz_sound(255, 1500);
}
