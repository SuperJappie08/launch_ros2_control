from setuptools import find_packages, setup

package_name = 'launch_ros2_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jasper van Brakel',
    maintainer_email='36795178+SuperJappie08@users.noreply.github.com',
    author='Jasper van Brakel',
    author_email='36795178+SuperJappie08@users.noreply.github.com',
    description='A launch extension for ros2_control',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'launch.frontend.launch_extension': [
            'launch_ros2_control = launch_ros2_control',
        ],
    },
)
