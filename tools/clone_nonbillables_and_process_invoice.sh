#!/bin/sh
set -xe

# Add deploy key to ssh config
mkdir -p ~/.ssh
if [ ! -e ~/.ssh/config ]; then
    touch ~/.ssh/config
    touch ~/.ssh/id_nonbillable
    echo "
    Host github-nonbillable
        HostName github.com
        IdentityFile ~/.ssh/id_nonbillable
    " > ~/.ssh/config
    echo "$GH_NONBILLABLE_DEPLOYKEY" > ~/.ssh/id_nonbillable
    chmod 600 ~/.ssh/id_nonbillable
fi

if [ ! -d ~/.ssh/known_hosts ]; then
    touch ~/.ssh/known_hosts
    echo "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
    github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=
    github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk=
    " >> ~/.ssh/known_hosts
fi

if [ ! -d ./non-billable-projects ]; then
    git clone git@github-nonbillable:CCI-MOC/non-billable-projects.git ./non-billable-projects
fi

INVOICE_MONTH=$(date --date="$(date +%Y-%m-01) -1 month" +%Y-%m)
export B2_ENDPOINT
export B2_APP_KEY
export B2_KEY_ID
export B2_BUCKET_NAME
python process_report/process_report.py \
    --invoice-month $INVOICE_MONTH \
    --pi-file ./non-billable-projects/pi.txt \
    --projects-file ./non-billable-projects/projects.txt \
    --timed-projects-file ./non-billable-projects/timed_projects.txt \
    --old-pi-file old_pi.csv
