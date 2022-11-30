from gooey import Gooey, GooeyParser
from PIL import Image
import av

from sims_reia import ReiaFile, ReiaFrame, write_reia_file, read_from_file

import sys


def run_converter_to_reia(args):
    try:
        container = av.open(args.input_video)
    except av.error.InvalidDataError:
        print("[Error] Input file could not be opened as a video")
        sys.exit(1)

    video = container.streams.video[0]

    # Sims needs .reia resolutions to be a square n by n.
    needs_resize = True
    if args.resize:
        target_width = 192
        target_height = 192
    else:
        if (
            video.width == video.height
            and (video.width % 32) == 0
            and (video.height % 32) == 0
        ):
            needs_resize = False
        target_resolution = max(video.width, video.height)
        target_width = (target_resolution // 32) * 32
        target_height = (target_resolution // 32) * 32
    print(f"Output resolution: {target_width}x{target_height}")

    # This is really horrible but if `video.frames` returns 0 we iterate decoding
    # the whole video once to get the number of frames.
    num_frames = video.frames
    if num_frames == 0:
        for _ in container.decode(video=0):
            num_frames += 1
        container = av.open(args.input_video)
        video = container.streams.video[0]

    def frame_generator():
        for frame in container.decode(video=0):
            print(f"progress: {frame.index}/{num_frames}")
            as_image = frame.to_image()
            if needs_resize:
                as_image = as_image.resize(
                    (target_width, target_height), resample=Image.Resampling.LANCZOS
                )
            yield ReiaFrame(as_image)

    fps = video.guessed_rate
    # Just assume a default fps if libav can't guess one :/
    if fps is None:
        fps = 24

    reia_file = ReiaFile(
        width=target_width,
        height=target_height,
        frames_per_second=fps,
        num_frames=num_frames,
        frames=frame_generator(),
    )
    with open(args.output_reia, "wb") as f:
        write_reia_file(reia_file, f)
    print(f"Wrote out {args.output_reia}")


def run_extract_from_reia(args):
    with open(args.input_reia, "rb") as f:
        reia_file = read_from_file(f)

        for i, frame in enumerate(reia_file.frames):
            print(f"progress: {i}/{reia_file.num_frames}")
            frame.image.save(f"{args.output_folder}/reia_frame{i:04}.png")


def initialize_convert_to_reia_parser(parser):
    input_group = parser.add_argument_group("Input Options")
    input_group.add_argument(
        "input_video",
        metavar="Input video file",
        help=(
            "The video file to convert (.gif/.mp4/.mkv etc)\n"
            "\n"
            "Try to keep the resolution low (under 256 pixels in width and height) and "
            "use an aspect ratio of 4:3 for best results."
        ),
        widget="FileChooser",
    )
    input_group.add_argument(
        "--resize",
        metavar="Resize to 192x192",
        default=True,
        action="store_true",
        help=(
            "Automatically resize video to default Sims 2 resolution.\n"
            "\n"
            "(Disabling this may lead to very large .reia files for higher "
            "resolution videos.)"
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
