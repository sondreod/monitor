import subprocess


def run_command(command: str):

    result = subprocess.run([command], shell=True, capture_output=True, text=True)
    err = result.stderr
    if err:
        raise RuntimeError(err)
    return result.stdout.splitlines()
