from setuptools import setup, find_packages

setup(
    name="juggling_tracker",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.19.0",
        "opencv-python>=4.5.0",
        "pyrealsense2>=2.50.0",
        "mediapipe>=0.8.10",
    ],
    entry_points={
        "console_scripts": [
            "juggling-tracker=juggling_tracker.main:main",
        ],
    },
    author="Juggling Tracker Team",
    author_email="example@example.com",
    description="A robust juggling ball tracking system",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/juggling-tracker",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)