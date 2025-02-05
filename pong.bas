SCREEN 13 ' Set 320x200 resolution with 256 colors
CLS

' Constants for game
CONST PADDLE_HEIGHT = 40
CONST PADDLE_WIDTH = 10
CONST BALL_SIZE = 4
CONST SCREEN_WIDTH = 320
CONST SCREEN_HEIGHT = 200
CONST PADDLE_SPEED = 5
CONST BALL_SPEED = 3

' Initial positions
leftPaddleY = (SCREEN_HEIGHT - PADDLE_HEIGHT) / 2
rightPaddleY = (SCREEN_HEIGHT - PADDLE_HEIGHT) / 2
ballX = SCREEN_WIDTH / 2
ballY = SCREEN_HEIGHT / 2
ballDX = BALL_SPEED
ballDY = BALL_SPEED

' Score variables
leftScore = 0
rightScore = 0

' Main game loop
DO
    ' Clear screen
    CLS
    
    ' Draw scores
    LOCATE 1, 10
    PRINT leftScore
    LOCATE 1, 30
    PRINT rightScore
    
    ' Draw paddles
    LINE (0, leftPaddleY)-(PADDLE_WIDTH, leftPaddleY + PADDLE_HEIGHT), 15, BF
    LINE (SCREEN_WIDTH - PADDLE_WIDTH, rightPaddleY)-(SCREEN_WIDTH, rightPaddleY + PADDLE_HEIGHT), 15, BF
    
    ' Draw ball
    CIRCLE (ballX, ballY), BALL_SIZE, 15
    PAINT (ballX, ballY), 15
    
    ' Move left paddle (W and S keys)
    k$ = INKEY$
    IF k$ = "w" OR k$ = "W" THEN
        leftPaddleY = leftPaddleY - PADDLE_SPEED
        IF leftPaddleY < 0 THEN leftPaddleY = 0
    END IF
    IF k$ = "s" OR k$ = "S" THEN
        leftPaddleY = leftPaddleY + PADDLE_SPEED
        IF leftPaddleY > SCREEN_HEIGHT - PADDLE_HEIGHT THEN leftPaddleY = SCREEN_HEIGHT - PADDLE_HEIGHT
    END IF
    
    ' Move right paddle (Up and Down arrow keys)
    IF k$ = CHR$(0) + "H" THEN
        rightPaddleY = rightPaddleY - PADDLE_SPEED
        IF rightPaddleY < 0 THEN rightPaddleY = 0
    END IF
    IF k$ = CHR$(0) + "P" THEN
        rightPaddleY = rightPaddleY + PADDLE_SPEED
        IF rightPaddleY > SCREEN_HEIGHT - PADDLE_HEIGHT THEN rightPaddleY = SCREEN_HEIGHT - PADDLE_HEIGHT
    END IF
    
    ' Move ball
    ballX = ballX + ballDX
    ballY = ballY + ballDY
    
    ' Ball collision with top and bottom
    IF ballY <= 0 OR ballY >= SCREEN_HEIGHT THEN
        ballDY = -ballDY
    END IF
    
    ' Ball collision with paddles
    IF ballX <= PADDLE_WIDTH AND ballY >= leftPaddleY AND ballY <= leftPaddleY + PADDLE_HEIGHT THEN
        ballDX = -ballDX
        ballDX = ballDX * 1.1 ' Increase speed slightly
    END IF
    
    IF ballX >= SCREEN_WIDTH - PADDLE_WIDTH AND ballY >= rightPaddleY AND ballY <= rightPaddleY + PADDLE_HEIGHT THEN
        ballDX = -ballDX
        ballDX = ballDX * 1.1 ' Increase speed slightly
    END IF
    
    ' Score points
    IF ballX <= 0 THEN
        rightScore = rightScore + 1
        ballX = SCREEN_WIDTH / 2
        ballY = SCREEN_HEIGHT / 2
        ballDX = BALL_SPEED
    END IF
    
    IF ballX >= SCREEN_WIDTH THEN
        leftScore = leftScore + 1
        ballX = SCREEN_WIDTH / 2
        ballY = SCREEN_HEIGHT / 2
        ballDX = -BALL_SPEED
    END IF
    
    ' Game speed control
    _DELAY 0.016 ' Approx 60 FPS
    
    ' Check for quit
    IF k$ = CHR$(27) THEN EXIT DO ' ESC to quit
LOOP

' End program
CLS
PRINT "Game Over!"
PRINT "Final Score:"
PRINT "Left Player: "; leftScore
PRINT "Right Player: "; rightScore
END
