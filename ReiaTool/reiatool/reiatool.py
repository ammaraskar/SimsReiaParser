from gooey import Gooey, GooeyParser
from PIL import Image
import av

from sims_reia import ReiaFile, ReiaFrame, write_reia_file

import sys
import textwrap


def run_converter_to_reia(args):
    print(args)

    container = av.open(args.input_video)
    video = container.streams.video[0]

    print(container.streams)
    print(
        video.height,
        video.width,
    )
    print(container)

    if video.height != video.width and not args.resize_video:
        print(
            "Video needs to be a square resolution, tick resize if you automatic resizing"
        )
        sys.exit(1)
    if ((video.height % 32) != 0) and not args.resize_video:
        print("Video resolution needs to be a multiple of 32, e.g 128x128")
        sys.exit(1)

    target_resolution = None
    # Okay not a multiple of 32 and they requested a resize.
    if (video.height % 32) != 0 and args.resize_video:
        target_resolution = max(video.height, video.width)
        # Find the nearest multiple of 32.
        target_resolution = (target_resolution // 32) * 32

    def frame_generator():
        for frame in container.decode(video=0):
            print(f"progress: {frame.index}/{video.frames}")
            as_image = frame.to_image()
            if target_resolution is not None:
                as_image = as_image.resize(
                    (target_resolution, target_resolution),
                    resample=Image.Resampling.LANCZOS,
                )
            yield ReiaFrame(as_image)

    file_resolution = video.height
    if target_resolution is not None:
        file_resolution = target_resolution

    reia_file = ReiaFile(
        width=file_resolution,
        height=file_resolution,
        frames_per_second=video.average_rate,
        num_frames=video.frames,
        frames=frame_generator(),
    )
    with open(args.output_reia, "wb") as f:
        write_reia_file(reia_file, f)


def run_extract_from_reia(args):
    pass


def initialize_convert_to_reia_parser(parser):
    input_group = parser.add_argument_group("Input Options")
    input_group.add_argument(
        "input_video",
        metavar="Input video file",
        help=textwrap.dedent(
            """\
        The video file to convert (.gif/.mp4/.mkv etc)
        
        Resolution should be a square and a multiple of 32 such as:
        128x128, 256x256, 512x512"""
        ),
        widget="FileChooser",
    )
    input_group.add_argument(
        "--resize-video",
        metavar="Resize video",
        default=False,
        action="store_true",
        help=textwrap.dedent(
            """\
        Resize the input video frames to the resolution requirements.
        
        (Note it is better to do this yourself in the video before-hand as
         this may degrade the quality.)"""
        ),
        widget="BlockCheckbox",
    )

    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "output_reia",
        metavar="Output .reia file",
        help="Where to save the converted .reia file to",
        widget="FileSaver",
        gooey_options={
            "wildcard": "REIA (*.reia)|*.reia|All files (*.*)|*.*",
            "default_file": "Neighborhood.reia",
        },
    )


def initialize_extract_reia_frames_parser(parser):
    input_group = parser.add_argument_group("Input Options")
    input_group.add_argument(
        "input_reia",
        metavar="Input .reia file",
        help="The .reia file whose frames you want to extract",
        widget="FileChooser",
        gooey_options={"wildcard": "REIA (*.reia)|*.reia|All files (*.*)|*.*"},
    )

    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "output_folder",
        metavar="Output folder for frames",
        help="Where to save the extracted frames from the .reia file to",
        widget="DirChooser",
    )


@Gooey(program_name="Sims2 .reia Tool", navigation="TABBED", default_size=(610, 680))
def main():
    parser = GooeyParser(description="Tools for working with .reia files")

    subparsers = parser.add_subparsers()

    convert_to_reia_parser = subparsers.add_parser(
        "convert", prog="Convert video to .reia"
    )
    initialize_convert_to_reia_parser(convert_to_reia_parser)
    convert_to_reia_parser.set_defaults(func=run_converter_to_reia)

    extract_reia_parser = subparsers.add_parser(
        "extract", prog="Extract frames from .reia"
    )
    initialize_extract_reia_frames_parser(extract_reia_parser)
    extract_reia_parser.set_defaults(func=run_extract_from_reia)

    args = parser.parse_args()
    # Calls the set_defaults(func=...) we set above with the args.
    args.func(args)


if __name__ == "__main__":
    main()
