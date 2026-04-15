# Development-Project-Security-Robot

## Setup

- Make sure that battery of vexbrain and controller are charged.
- Connect battery to brain.
- Place raspberry pi and its battery onto the front of the robot so the camera is facing forward.
- Turn on raspberry pi & run 'python3 bot_commands.py'.
- Turn on brain and connect controller and run the program.

## Vex operations

- Drive around using the joysticks (right joystick controls forwards and backwards movement, left joystick controls turning).
- Can increase or decrease the speed the robot moves at by pressing the arrows.
- Once familiar with controls you can press r1 to start recording a path.
- Drive around path you would like robot to go around and press l2 once you get to the end of your path. (Only use one joystick at a time when recording a path).
- Press R2 to run the loop.
- If you wish to pause the robot momentarily hold down the pause button and when you wish for it to continue let go of the button.
- When you want to end the loop press L2 on the robot and you will be given back control to drive around.

## Pi operations

- After creating the loop that you would like send '/begin' on Telegram to tell the pi to turn on the camera detection and also '/stop' to end it.
- If the camera detects a person with a certainty of 45% a capture of what the camera sees will be taken and sent to the Telegram chat so the user can see what the security alert is.
- On the telegram the user is able to message the word 'save' to keep the photo of the image in the chat and if the user sends 'ok' instead then it deletes the image and allows the user to continue.
- User is able to send '/status' to get a live status on the robots current conditions.
- User is able to send '/capture' to take a photo if they want to take a photo of something at any time.
- They can also ask '/help' for a list of commands and help on how the pi is working.


## References
- For the person detection on the PI we use a pretrained model that uses MobileNetSSD, here is a link to that Github repo: https://github.com/nikmart/pi-object-detection
- For creating the physical car for the robot it was based on this model https://instructions.online/?id=4095-exp%20speed%20build
- For designing the joystick controls to best suit the robot we learned about arcade drive from this website https://xiaoxiae.github.io/Robotics-Simplified-Website/drivetrain-control/arcade-drive/

