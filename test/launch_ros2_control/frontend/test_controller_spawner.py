# Copyright 2025 Jasper van Brakel
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import io
import textwrap

from launch import LaunchService
from launch.condition import Condition
from launch.frontend import Parser
from launch.utilities import perform_substitutions
import osrf_pycommon.process_utils


def test_launch_controller_spawner_yaml():
    yaml_file = textwrap.dedent(
        r"""
        launch:
            - controller_spawner:
                controller_manager: /my/controller_manager
                controller:
                    -   name: my_controller
                        remap:
                            -   from: me
                                to: /you
                    -   name: second_controller
                        # Have to pass explicitly as str, since it is not using a substitution
                        if: 'True'
                        remap:
                            -   from: something
                                to: else
        """
    )
    with io.StringIO(yaml_file) as f:
        check_launch_controller_spawner(f)


def test_launch_controller_spawner_xml():
    xml_file = textwrap.dedent(
        r"""
        <launch>
            <controller_spawner controller_manager="/my/controller_manager">
                <controller name="my_controller">
                    <remap from="me" to="/you" />
                </controller>
                <controller name="second_controller" if="True">
                    <remap from="something" to="else" />
                </controller>
            </controller_spawner>
        </launch>
        """  # noqa: E501
    )
    with io.StringIO(xml_file) as f:
        check_launch_controller_spawner(f)


def check_launch_controller_spawner(file):
    root_entity, parser = Parser.load(file)
    ld = parser.parse_description(root_entity)
    ls = LaunchService()
    ls.include_launch_description(ld)

    loop = osrf_pycommon.process_utils.get_loop()
    launch_task = loop.create_task(ls.run_async())

    controller_spawner, = ld.describe_sub_entities()
    my_controller = controller_spawner._ControllerSpawner__controller_descriptions[0]
    second_controller = controller_spawner._ControllerSpawner__controller_descriptions[1]

    def perform(substitution):
        return perform_substitutions(ls.context, substitution)

    # TODO: Check Controller Spawner params
    assert (
        perform(controller_spawner._ControllerSpawner__controller_manager) ==
        '/my/controller_manager'
    )

    # Check Controller params
    my_controller_remappings = list(my_controller.remappings)
    second_controller_remappings = list(second_controller.remappings)

    assert perform(my_controller.controller_name) == 'my_controller'
    assert my_controller.condition is None
    assert (perform(my_controller_remappings[0][0]),
            perform(my_controller_remappings[0][1])) == ('me', '/you')
    assert len(my_controller_remappings) == 1

    assert perform(second_controller.controller_name) == 'second_controller'
    assert isinstance(second_controller.condition, Condition)
    assert second_controller.condition.evaluate(ls.context)
    assert (perform(second_controller_remappings[0][0]),
            perform(second_controller_remappings[0][1])) == ('something', 'else')

    # TODO: This executes the spawner, but the spawner will not actually run,
    #       since there is no controller manager.
    timeout_sec = 5
    loop.run_until_complete(asyncio.sleep(timeout_sec))
    if not launch_task.done():
        loop.create_task(ls.shutdown())
        loop.run_until_complete(launch_task)
    assert 0 == launch_task.result()
