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

"""Module for the controller_spawner action."""

# import pathlib
import itertools
from typing import List, Optional

from launch.action import Action
from launch.frontend import Entity, expose_action, Parser
from launch.launch_context import LaunchContext
from launch.some_substitutions_type import SomeSubstitutionsType
from launch_ros.actions import Node

from ..descriptions import Controller


@expose_action('controller_spawner')
@expose_action('controller-spawner')
class ControllerSpawner(Action):
    def __init__(
        self,
        *,
        controller_descriptions: List[Controller],
        spawner_name: Optional[SomeSubstitutionsType] = None,
        controller_manager: Optional[SomeSubstitutionsType] = None,
        # controller_remappings: Optional[SomeRemapRules] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.__controller_descriptions = controller_descriptions
        self.__spawner_name = spawner_name
        self.__controller_manager = controller_manager

    @classmethod
    def parse(cls, entity: Entity, parser: Parser):
        """Parse controller_spawner."""
        _, kwargs = super().parse(entity, parser)

        spawner_name = entity.get_attr('spawner_name', data_type=str, optional=True)
        if spawner_name is not None:
            kwargs['spawner_name'] = parser.parse_substitution(spawner_name)

        controller_manager = entity.get_attr(
            'controller_manager', data_type=str, optional=True
        )
        if controller_manager is not None:
            kwargs['controller_manager'] = parser.parse_substitution(controller_manager)

        controllers = entity.get_attr('controller', data_type=List[Entity])
        kwargs['controller_descriptions'] = []
        for controller in controllers:
            controller_cls, controller_kwargs = Controller.parse(parser, controller)
            kwargs['controller_descriptions'].append(
                controller_cls(**controller_kwargs)
            )

        return cls, kwargs

    def execute(self, context: LaunchContext) -> Optional[List[Action]]:
        """Execute the action."""
        launch_descriptions: List[Action] = []

        controllers: List[SomeSubstitutionsType] = []
        other_arguments: List[SomeSubstitutionsType] = []

        if self.__controller_manager is not None:
            other_arguments += ['--controller-manager', self.__controller_manager]

        for controller in self.__controller_descriptions:
            if controller.condition is not None and not controller.condition.evaluate(context):
                continue

            controllers.append(controller.controller_name)

            # FIXME: NEEDS TO BE A FILE --param works but cannot specify target
            # if controller.parameters:
            #     evaluated_parameters = evaluated_parameters(context,controller.parameters)
            #     for params in evaluated_parameters:
            #         is_file = False
            #         if isinstance(params, dict):
            #             params_argument = controller._create_params_file_from_dict(params)
            #             is_file = True
            #         elif isinstance(params, pathlib.Path):
            #             params_argument = str(params)
            #             is_file = True
            #         elif isinstance(params, Parameter):
            #             params_argument =

            if controller.remappings:
                for from_topic, to_topic in controller.remappings:
                    other_arguments += [
                        '--controller-ros-args',
                        itertools.chain.from_iterable((
                            '-r ',
                            controller.controller_name,
                            ':',
                            from_topic,
                            ':=',
                            to_topic,
                        )),
                    ]

        launch_descriptions.append(
            Node(
                package='controller_manager',
                executable='spawner',
                name=self.__spawner_name,
                arguments=controllers + other_arguments,
            )
        )

        return launch_descriptions
