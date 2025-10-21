"""Test Athena managed query results support."""

from unittest.mock import MagicMock, patch

from awswrangler.athena._utils import _get_workgroup_config, _start_query_execution, _WorkGroupConfig


def test_workgroup_config_with_managed_results():
    """Test that _WorkGroupConfig includes managed_results field."""
    config = _WorkGroupConfig(enforced=False, s3_output=None, encryption=None, kms_key=None, managed_results=True)
    assert config.managed_results is True


def test_workgroup_config_without_managed_results():
    """Test that _WorkGroupConfig defaults managed_results to False."""
    config = _WorkGroupConfig(enforced=False, s3_output=None, encryption=None, kms_key=None, managed_results=False)
    assert config.managed_results is False


@patch("awswrangler.athena._utils.get_work_group")
def test_get_workgroup_config_detects_managed_results(mock_get_work_group):
    """Test that _get_workgroup_config detects ManagedQueryResultsConfiguration."""
    mock_get_work_group.return_value = {
        "WorkGroup": {
            "Configuration": {
                "EnforceWorkGroupConfiguration": False,
                "ResultConfiguration": {"OutputLocation": "s3://bucket/path"},
                "ManagedQueryResultsConfiguration": {"Enabled": True},
            }
        }
    }

    config = _get_workgroup_config(workgroup="test-workgroup")
    assert config.managed_results is True


@patch("awswrangler.athena._utils.get_work_group")
def test_get_workgroup_config_without_managed_results(mock_get_work_group):
    """Test that _get_workgroup_config handles workgroups without managed results."""
    mock_get_work_group.return_value = {
        "WorkGroup": {
            "Configuration": {
                "EnforceWorkGroupConfiguration": False,
                "ResultConfiguration": {"OutputLocation": "s3://bucket/path"},
            }
        }
    }

    config = _get_workgroup_config(workgroup="test-workgroup")
    assert config.managed_results is False


@patch("awswrangler.athena._utils.get_work_group")
def test_get_workgroup_config_with_managed_results_disabled(mock_get_work_group):
    """Test that _get_workgroup_config handles ManagedQueryResultsConfiguration with Enabled=False."""
    mock_get_work_group.return_value = {
        "WorkGroup": {
            "Configuration": {
                "EnforceWorkGroupConfiguration": False,
                "ResultConfiguration": {"OutputLocation": "s3://bucket/path"},
                "ManagedQueryResultsConfiguration": {"Enabled": False},
            }
        }
    }

    config = _get_workgroup_config(workgroup="test-workgroup")
    assert config.managed_results is False


@patch("awswrangler.athena._utils._utils.client")
@patch("awswrangler.athena._utils._utils.try_it")
def test_start_query_execution_skips_result_config_with_managed_results(mock_try_it, mock_client):
    """Test that _start_query_execution does not set ResultConfiguration when managed results are enabled."""
    mock_client.return_value = MagicMock()
    mock_try_it.return_value = {"QueryExecutionId": "test-query-id"}

    wg_config = _WorkGroupConfig(enforced=False, s3_output=None, encryption=None, kms_key=None, managed_results=True)

    query_id = _start_query_execution(
        sql="SELECT 1", wg_config=wg_config, database="test_db", workgroup="test-workgroup"
    )

    # Verify the call was made
    assert query_id == "test-query-id"
    mock_try_it.assert_called_once()

    # Check that ResultConfiguration was NOT included in the arguments
    call_kwargs = mock_try_it.call_args[1]
    assert "ResultConfiguration" not in call_kwargs
    assert call_kwargs["QueryString"] == "SELECT 1"


@patch("awswrangler.athena._utils._utils.client")
@patch("awswrangler.athena._utils._utils.try_it")
@patch("awswrangler.athena._utils._get_s3_output")
def test_start_query_execution_includes_result_config_without_managed_results(
    mock_get_s3_output, mock_try_it, mock_client
):
    """Test that _start_query_execution sets ResultConfiguration when managed results are disabled."""
    mock_client.return_value = MagicMock()
    mock_try_it.return_value = {"QueryExecutionId": "test-query-id"}
    mock_get_s3_output.return_value = "s3://bucket/path"

    wg_config = _WorkGroupConfig(
        enforced=False, s3_output="s3://bucket/path", encryption=None, kms_key=None, managed_results=False
    )

    query_id = _start_query_execution(
        sql="SELECT 1", wg_config=wg_config, database="test_db", workgroup="test-workgroup"
    )

    # Verify the call was made
    assert query_id == "test-query-id"
    mock_try_it.assert_called_once()

    # Check that ResultConfiguration WAS included in the arguments
    call_kwargs = mock_try_it.call_args[1]
    assert "ResultConfiguration" in call_kwargs
    assert call_kwargs["ResultConfiguration"]["OutputLocation"] == "s3://bucket/path"
