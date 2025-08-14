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

"""Module for the spawn_controller action."""

import itertools
import os
from pathlib import Path
from typing import List, Optional

import launch
from launch.action import Action
from launch.frontend import Entity, expose_action, Parser
from launch.launch_context import LaunchContext
from launch.some_substitutions_type import SomeSubstitutionsType
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import Parameter, ParameterFile, ParameterValue
from launch_ros.utilities import evaluate_parameters
from launch_ros.utilities.normalize_parameters import normalize_parameter_dict

from ..descriptions import Controller


@expose_action('spawn_controller')
@expose_action('spawn-controller')
class SpawnControllers(Action):
    def __init__(
        self,
        *,
        controller_descriptions: List[Controller],
        spawner_name: Optional[SomeSubstitutionsType] = None,
        controller_manager: Optional[SomeSubstitutionsType] = None,
        # controller_remappings: Optional[SomeRemapRules] = None,
        **kwargs,
    ) -> None:
        """
        Construct a SpawnControllers.

        :param controller_descriptions: descriptions of controllers to be spawned
        :param spawner_name: the spawner node name
        :param controller_manager: the controller manager node spawn the controllers into
        """
        super().__init__(**kwargs)

        self.__controller_descriptions = controller_descriptions
        self.__spawner_name = spawner_name
        self.__controller_manager = controller_manager

        self.__logger = launch.logging.get_logger(__name__)

    @classmethod
    def parse(cls, entity: Entity, parser: Parser):
        """Parse spawn_controller."""
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

        # Parse global params
        params_container = context.launch_configurations.get('global_params', None)
        extra_params = []

        if params_container is not None:
            for param in params_container:
                if isinstance(param, tuple):
                    extra_params.append(normalize_parameter_dict({param[0]: param[1]}))
                else:
                    param_file_path = Path(param).resolve()
                    assert param_file_path.is_file()
                    extra_params.append(ParameterFile(param_file_path))

        for controller in self.__controller_descriptions:
            if controller.condition is not None and not controller.condition.evaluate(context):
                continue

            controllers.append(controller.controller_name)

            if controller.parameters or extra_params:
                combined_parameters = extra_params.copy()

                if controller.parameters:
                    combined_parameters += controller.parameters

                evaluated_parameters = evaluate_parameters(context, combined_parameters)

                # Load normally for dict and path/file, since no combined file needs to be made
                # TODO(SuperJappie08): It would be nice to combine continues sections of Paramaters
                #                      into a single file, since it would prevent a lot of files.
                for params in evaluated_parameters:
                    if isinstance(params, dict):
                        params_argument = controller._create_params_file_from_dict(context, params)
                        assert os.path.isfile(params_argument)
                    elif isinstance(params, Path):
                        params_argument = str(params)
                    elif isinstance(params, Parameter):
                        # NOTE: This only occurs, if somebody explicitly passes a Parameter object
                        # FIXME(SuperJappie08): This makes a lot of temporary files, could combine
                        #                       the values if present (and non-interrupted).
                        params_dict = normalize_parameter_dict({
                            params.name: ParameterValue(params.value, value_type=params.value_type)
                        })
                        params_argument = controller._create_params_file_from_dict(
                            context,
                            params_dict
                        )
                        assert os.path.isfile(params_argument)
                    else:
                        raise RuntimeError('invalid normalized parameters {}'.format(repr(params)))

                    if not os.path.isfile(params_argument):
                        self.__logger.warning(
                            'Parameter file path is not a file: {}'.format(params_argument),
                        )
                        continue
                    other_arguments += ['-p', params_argument]

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
