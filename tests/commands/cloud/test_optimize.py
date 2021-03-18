# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.components.config.optimizer_config_manager import NodeType
from lean.container import container
from lean.models.api import QCOptimization, QCOptimizationEstimate
from lean.models.optimizer import (OptimizationConstraint, OptimizationExtremum, OptimizationParameter,
                                   OptimizationTarget)
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory


def create_api_optimization() -> QCOptimization:
    return QCOptimization(
        optimizationId="123",
        projectId=1,
        status="completed",
        name="Optimization name",
        backtests={},
        runtimeStatistics={}
    )


@pytest.fixture(autouse=True)
def optimizer_config_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the optimizer config manager before every test."""
    optimizer_config_manager = mock.Mock()
    optimizer_config_manager.configure_strategy.return_value = "QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy"
    optimizer_config_manager.configure_target.return_value = OptimizationTarget(
        target="TotalPerformance.PortfolioStatistics.SharpeRatio",
        extremum=OptimizationExtremum.Maximum)

    optimizer_config_manager.configure_parameters.return_value = [
        OptimizationParameter(name="param1", min=1.0, max=10.0, step=0.5)
    ]

    optimizer_config_manager.configure_constraints.return_value = [
        OptimizationConstraint(**{"target": "TotalPerformance.PortfolioStatistics.Drawdown",
                                  "operator": "less",
                                  "target-value": "0.25"})
    ]

    optimizer_config_manager.configure_node.return_value = NodeType(name="O8-16",
                                                                    ram=16,
                                                                    cores=8,
                                                                    price=0.6,
                                                                    min_nodes=1,
                                                                    max_nodes=6,
                                                                    default_nodes=3), 3

    container.optimizer_config_manager.override(providers.Object(optimizer_config_manager))
    return optimizer_config_manager


def test_cloud_optimize_runs_optimization_by_project_id() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    container.api_client.override(providers.Object(api_client))

    cloud_runner = mock.Mock()
    cloud_runner.run_optimization.return_value = optimization
    container.cloud_runner.override(providers.Object(cloud_runner))

    result = CliRunner().invoke(lean, ["cloud", "optimize", "1"])

    assert result.exit_code == 0

    cloud_runner.run_optimization.assert_called_once()
    args, kwargs = cloud_runner.run_optimization.call_args

    assert args[0] == project


def test_cloud_optimize_runs_optimization_by_project_name() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=1000, balance=10)
    container.api_client.override(providers.Object(api_client))

    cloud_runner = mock.Mock()
    cloud_runner.run_optimization.return_value = optimization
    container.cloud_runner.override(providers.Object(cloud_runner))

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project"])

    assert result.exit_code == 0

    cloud_runner.run_optimization.assert_called_once()
    args, kwargs = cloud_runner.run_optimization.call_args

    assert args[0] == project


def test_cloud_optimize_uses_given_name() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    container.api_client.override(providers.Object(api_client))

    cloud_runner = mock.Mock()
    cloud_runner.run_optimization.return_value = optimization
    container.cloud_runner.override(providers.Object(cloud_runner))

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project", "--name", "My Name"])

    assert result.exit_code == 0

    cloud_runner.run_optimization.assert_called_once()
    args, kwargs = cloud_runner.run_optimization.call_args

    assert args[2] == "My Name"


def test_cloud_optimize_passes_given_config_to_cloud_runner() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    container.api_client.override(providers.Object(api_client))

    cloud_runner = mock.Mock()
    cloud_runner.run_optimization.return_value = optimization
    container.cloud_runner.override(providers.Object(cloud_runner))

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project", "--name", "My Name"])

    assert result.exit_code == 0

    optimizer_config_manager = container.optimizer_config_manager()
    cloud_runner.run_optimization.assert_called_once_with(project,
                                                          mock.ANY,
                                                          "My Name",
                                                          optimizer_config_manager.configure_strategy(cloud=True),
                                                          optimizer_config_manager.configure_target(),
                                                          optimizer_config_manager.configure_parameters([]),
                                                          optimizer_config_manager.configure_constraints(),
                                                          optimizer_config_manager.configure_node()[0].name,
                                                          optimizer_config_manager.configure_node()[1])


def test_cloud_optimize_pushes_project_when_push_option_given() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "Python Project")
    optimization = create_api_optimization()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    container.api_client.override(providers.Object(api_client))

    cloud_runner = mock.Mock()
    cloud_runner.run_optimization.return_value = optimization
    container.cloud_runner.override(providers.Object(cloud_runner))

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "optimize", "Python Project", "--push"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once_with([Path.cwd() / "Python Project"])


def test_cloud_optimize_pushes_nothing_when_project_does_not_exist_locally() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    container.api_client.override(providers.Object(api_client))

    cloud_runner = mock.Mock()
    cloud_runner.run_optimization.return_value = optimization
    container.cloud_runner.override(providers.Object(cloud_runner))

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project", "--push"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_not_called()


def test_cloud_optimize_aborts_when_optimization_fails() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")

    def run_optimization(*args, **kwargs):
        raise RuntimeError("Oops")

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    container.api_client.override(providers.Object(api_client))

    cloud_runner = mock.Mock()
    cloud_runner.run_optimization.side_effect = run_optimization
    container.cloud_runner.override(providers.Object(cloud_runner))

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project"])

    assert result.exit_code != 0

    cloud_runner.run_optimization.assert_called_once()


def test_cloud_optimize_aborts_when_input_matches_no_cloud_project() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    container.api_client.override(providers.Object(api_client))

    cloud_runner = mock.Mock()
    cloud_runner.run_optimization.return_value = optimization
    container.cloud_runner.override(providers.Object(cloud_runner))

    result = CliRunner().invoke(lean, ["cloud", "optimize", "Fake Project"])

    assert result.exit_code != 0

    cloud_runner.run_optimization.assert_not_called()