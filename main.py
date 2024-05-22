import sys
import pygame
import pyperclip
from pygame.locals import *
from constants import *
from text_editor import TextEditor


pygame.init()
pygame.key.set_repeat(300, 50)  # Start repeating after 300ms, repeat every 50ms thereafter

tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption('Code Wizard')

fonte = pygame.font.SysFont('arial', 24)

if __name__ == "__main__":

    # Create an instance of your TextEditor
    editor = TextEditor(fonte)

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        editor.load_file(filename)

    rodando = True
    clock = pygame.time.Clock()

    # Create a list to store frames
    frames = []

    while rodando:
        for event in pygame.event.get():
            if event.type == QUIT:
                rodando = False
            elif event.type == KEYDOWN:
                editor.input(event)

        editor.draw(tela)
        pygame.display.flip()

        # Capture the frame and append to the list
        frame_data = pygame.surfarray.array3d(pygame.display.get_surface())
        frames.append(frame_data.transpose([1, 0, 2]))

        clock.tick(60)

    pygame.quit()

    # Save frames as MP4 video
    imageio.mimwrite('output_video.mp4', frames, fps=60)
