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

from tempfile import NamedTemporaryFile
from typing import List, Optional

from launch.condition import Condition
from launch.conditions import IfCondition, UnlessCondition
from launch.frontend import Entity, Parser
from launch.some_substitutions_type import SomeSubstitutionsType
from launch.substitution import Substitution
from launch.utilities import normalize_to_list_of_substitutions
from launch_ros.parameters_type import Parameters, SomeParameters
from launch_ros.remap_rule_type import RemapRules, SomeRemapRules
from launch_ros.utilities import normalize_parameters, normalize_remap_rules
import yaml


class Controller:
    """Describes a ROS2 Control Controller."""

    def __init__(
        self,
        *,
        name: SomeSubstitutionsType,
        parameters: Optional[SomeParameters] = None,
        remappings: Optional[SomeRemapRules] = None,
        condition: Optional[Condition] = None
    ) -> None:
        self.__controller_name = normalize_to_list_of_substitutions(name)

        self.__parameters = None  # type: Optional[Parameters]
        if parameters:
            self.__parameters = normalize_parameters(parameters)

        self.__remappings = None  # type: Optional[RemapRules]
        if remappings:
            self.__remappings = normalize_remap_rules(remappings)

        self.__condition = condition

    @classmethod
    def parse(cls, parser: Parser, entity: Entity):
        """Parse controller."""
        from launch_ros.actions import Node

        kwargs = {}

        kwargs['name'] = parser.parse_substitution(entity.get_attr('name'))

        if_cond = entity.get_attr('if', optional=True)
        unless_cond = entity.get_attr('unless', optional=True)
        if if_cond is not None and unless_cond is not None:
            raise RuntimeError("if and unless are conditions and can't be used simultaneously")
        if if_cond is not None:
            kwargs['condition'] = IfCondition(
                predicate_expression=parser.parse_substitution(if_cond)
            )
        if unless_cond is not None:
            kwargs['condition'] = UnlessCondition(
                predicate_expression=parser.parse_substitution(unless_cond)
            )

        parameters = entity.get_attr('param', data_type=List[Entity], optional=True)
        if parameters is not None:
            kwargs['parameters'] = Node.parse_nested_parameters(parameters, parser)

        remappings = entity.get_attr('remap', data_type=List[Entity], optional=True)
        if remappings is not None:
            kwargs['remappings'] = [
                (
                    parser.parse_substitution(remap.get_attr('from')),
                    parser.parse_substitution(remap.get_attr('to'))
                ) for remap in remappings
            ]

            for remap in remappings:
                remap.assert_entity_completely_parsed()

        entity.assert_entity_completely_parsed()

        return cls, kwargs

    @property
    def controller_name(self) -> List[Substitution]:
        """Get the name of the controller as a sequence of substitutions to be performed."""
        return self.__controller_name

    @property
    def parameters(self) -> Optional[Parameters]:
        """Get the the controller YAML files or dicts with substitutions to be performed."""
        return self.__parameters

    @property
    def remappings(self) -> Optional[RemapRules]:
        """Get the the controller remappings as a sequence of substitutions to be performed."""
        return self.__remappings

    @property
    def condition(self) -> Optional[Condition]:
        """Getter for condition."""
        return self.__condition

    def _create_params_file_from_dict(self, params):
        with NamedTemporaryFile(mode='w', prefix='launch_params_', delete=False) as h:
            param_file_path = h.name
            param_dict = {
                f'/**/{self.controller_name}':
                {'ros__parameters': params}
            }
            yaml.dump(param_dict, h, default_flow_style=False)
            return param_file_path
