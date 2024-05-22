import sys
import pygame
import pyperclip
from pygame.locals import *
from constants import *
from text_editor import TextEditor
import imageio

pygame.init()
pygame.key.set_repeat(300, 50)  # Start repeating after 300ms, repeat every 50ms thereafter

tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption('Code Wizard')

fonte_path = pygame.font.match_font('arial')
fonte_size = 24

if __name__ == "__main__":

    # Create an instance of your TextEditor
    editor = TextEditor(fonte_path, fonte_size)

    if len(sys.argv) > 1 and sys.argv[1] != '--output-video':
        filename = sys.argv[1]
        editor.load_file(filename)

    rodando = True
    clock = pygame.time.Clock()

    # Check if --output-video is in the command line arguments
    output_video = '--output-video' in sys.argv

    # Create a list to store frames if output_video is True
    frames = [] if output_video else None

    while rodando:
        for event in pygame.event.get():
            if event.type == QUIT:
                rodando = False
            elif event.type == KEYDOWN:
                editor.input(event)
            elif event.type == MOUSEBUTTONDOWN or event.type == MOUSEBUTTONUP or event.type == MOUSEMOTION:
                editor.handle_mouse_event(event)

        editor.draw(tela)
        pygame.display.flip()

        # Capture the frame and append to the list if output_video is True
        if output_video:
            frame_data = pygame.surfarray.array3d(pygame.display.get_surface())
            frames.append(frame_data.transpose([1, 0, 2]))

        clock.tick(60)

    pygame.quit()

    # Save frames as MP4 video if output_video is True
    if output_video:
        imageio.mimwrite('output_video.mp4', frames, fps=60)
