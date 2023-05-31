#!/bin/sh

set -e

# use specified user name or use `default` if not specified
MY_USERNAME="${MY_USERNAME:-default}"

# use specified group name or use the same user name also as the group name
MY_GROUP="${MY_GROUP:-${MY_USERNAME}}"

# use the specified UID for the user
MY_UID="${MY_UID:-1000}"

# use the specified GID for the user
MY_GID="${MY_GID:-${MY_UID}}"

# check to see if group exists; if not, create it
if grep -q -E "^${MY_GROUP}:" /etc/group > /dev/null 2>&1
then
  echo "INFO: Group exists; skipping creation"
else
  echo "INFO: Group doesn't exist; creating..."
  # create the group
  addgroup -g "${MY_GID}" "${MY_GROUP}"
fi


# check to see if user exists; if not, create it
if id -u "${MY_USERNAME}" > /dev/null 2>&1
then
  echo "INFO: User exists; skipping creation"
else
  echo "INFO: User doesn't exist; creating..."
  # create the user
  adduser -u "${MY_UID}" -G "${MY_GROUP}" --disabled-password -h "/home/${MY_USERNAME}" -s /bin/bash "${MY_USERNAME}"
fi

# create home directory and set permissions
mkdir -p /home/"${MY_USERNAME}"
chown "${MY_UID}":"${MY_GID}" /home/"${MY_USERNAME}"

# verify that /app/.tox exists and that the permissions are correct
if [ ! -d "/app/.tox" ]
then
  mkdir "/app/.tox"
  chown "${MY_UID}":"${MY_GID}" "/app/.tox"
else
  # get current owner details
  OWNER="$(stat -c '%u' "/app/.tox")"
  GROUP="$(stat -c '%g' "/app/.tox")"

  # check to see if UID and GID match
  if [ "${OWNER}" != "${MY_UID}" ] || [ "${GROUP}" != "${MY_GID}" ]
  then
    # UID or GID doesn't match, set permissions
    echo "WARNING: owner or group (${OWNER}:${GROUP}) not set correctly on '/app/.tox'"
    echo "INFO: setting correct permissions (${MY_UID}:${MY_GID})"
    chown "${MY_UID}":"${MY_GID}" "/app/.tox"
  fi
fi

# start the CMD
echo "INFO: Running ${1} as ${MY_USERNAME}:${MY_GROUP} (${MY_UID}:${MY_GID})"

# exec and run the actual process specified in the CMD of the Dockerfile (which gets passed as ${*})
exec su-exec "${MY_USERNAME}" "${@}"