#!/bin/bash -i
set -e
unset HISTFILE

echo "*** Running post install script for ${INSTALLER_NAME} ..."

echo "Args = $@"
echo "Environment variables:"
env | sort
echo ""

# ---- Shortcut
pythonexe=${PREFIX}/bin/python
menuinst=${PREFIX}/bin/menuinst_cli.py
mode=$([[ -e "${PREFIX}/.nonadmin" ]] && echo "user" || echo "system")
shortcut_path=$($pythonexe $menuinst shortcut --mode=$mode)

# ---- Aliases
spy_exe="${PREFIX}/envs/griffin-runtime/bin/griffin"
u_spy_exe="${PREFIX}/uninstall-griffin.sh"

[[ "$OSTYPE" == "linux"* ]] && alias_text="alias griffin=${spy_exe}"
[[ "$mode" == "user" ]] && alias_text="${alias_text:+${alias_text}\n}alias uninstall-griffin=${u_spy_exe}"

m1="# >>> Added by Griffin >>>"
m2="# <<< Added by Griffin <<<"

add_alias() {
    if [[ ! -s "$shell_init" ]]; then
        echo -e "$m1\n${alias_text}\n$m2" > $shell_init
        return
    fi

    # BSD sed does not like semicolons; newlines work for both BSD and GNU.
    sed -i.bak -e "
    /$m1/,/$m2/{
        h
        /$m2/ s|.*|$m1\n$alias_text\n$m2|
        t
        d
    }
    \${
        x
        /^$/{
            s||\n$m1\n$alias_text\n$m2|
            H
        }
        x
    }" $shell_init
    rm $shell_init.bak
}

if [[ "$mode" == "system" && "$OSTYPE" == "darwin"* ]]; then
    shell_init_list=("/etc/zshrc" "/etc/bashrc")
elif [[ "$mode" == "system" ]]; then
    shell_init_list=("/etc/zsh/zshrc" "/etc/bash.bashrc")
else
    shell_init_list=("$HOME/.zshrc" "$HOME/.bashrc")
fi

for shell_init in ${shell_init_list[@]}; do
    # If shell rc path or alias_text is empty, don't do anything
    [[ -z "$shell_init" || -z "$alias_text" ]] && continue

    # Don't create non-existent global init file
    [[ "$mode" == "system" && ! -f "$shell_init" ]] && continue

    # Resolve possible symlink
    [[ -f $shell_init ]] && shell_init=$(readlink -f $shell_init)

    echo "Creating aliases in $shell_init ..."
    add_alias
done

# ---- Uninstall script
echo "Creating uninstall script..."
cat <<END > ${u_spy_exe}
#!/bin/bash

if [[ ! -w ${PREFIX} || ! -w "$shortcut_path" ]]; then
    echo "Uninstalling Griffin requires sudo privileges."
    exit 1
fi

while getopts "f" option; do
    case "\$option" in
        (f) force=true ;;
    esac
done
shift \$((\$OPTIND - 1))

if [[ -z \$force ]]; then
    cat <<EOF
You are about to uninstall Griffin.
If you proceed, aliases will be removed from:
  ${shell_init_list[@]}
and the following will be removed:
  ${shortcut_path}
  ${PREFIX}

Do you wish to continue?
EOF
    read -p " [yes|NO]: " confirm
    confirm=\$(echo \$confirm | tr '[:upper:]' '[:lower:]')
    if [[ ! "\$confirm" =~ ^y(es)?$ ]]; then
        echo "Uninstall aborted."
        exit 1
    fi
fi

# Quit Griffin
echo "Quitting Griffin..."
if [[ "\$OSTYPE" == "darwin"* ]]; then
    osascript -e 'quit app "$(basename "$shortcut_path")"' 2>/dev/null
else
    pkill griffin 2>/dev/null
fi
sleep 1
while [[ \$(pgrep griffin 2>/dev/null) ]]; do
    echo "Waiting for Griffin to quit..."
    sleep 1
done

# Remove aliases from shell startup
for x in ${shell_init_list[@]}; do
    # Resolve possible symlink
    [[ ! -f "\$x" ]] && continue || x=\$(readlink -f \$x)

    echo "Removing Griffin shell commands from \$x..."
    sed -i.bak -e "/$m1/,/$m2/d" \$x
    rm \$x.bak
done

# Remove shortcut and environment
echo "Removing Griffin shortcut and environment..."
$pythonexe $menuinst remove

rm -rf ${PREFIX}

echo "Griffin successfully uninstalled."
END
chmod +x ${u_spy_exe}

# ---- Linux post-install notes
if [[ "$OSTYPE" == "linux"* ]]; then
    cat <<EOF

###############################################################################
#                             !!! IMPORTANT !!!
###############################################################################
Griffin can be launched by standard methods in Gnome and KDE desktop
environments. It can also be launched from the command line on all Linux
distributions with the command:

$ griffin

EOF
    if [[ "$mode" == "system" ]]; then
        cat <<EOF
This command will only be available in new shell sessions.

To uninstall Griffin, run the following from the command line:

$ sudo $PREFIX/uninstall-griffin.sh

EOF
    else
        cat <<EOF
To uninstall Griffin, run the following from the command line:

$ uninstall-griffin

These commands will only be available in new shell sessions. To make them
available in this session, you must source your $shell_init file with:

$ source $shell_init

EOF
    fi
    cat <<EOF
###############################################################################

EOF
fi

echo "*** Post install script for ${INSTALLER_NAME} complete"

# ---- Launch Griffin
if [[ -n "$CI" || "$INSTALLER_UNATTENDED" == "1" || "$COMMAND_LINE_INSTALL" == "1" ]]; then
    echo Installing in batch mode, do not launch Griffin
    exit 0
fi

echo "Launching Griffin now..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    launch_script=${TMPDIR:-$SHARED_INSTALLER_TEMP}/post-install-launch.sh
    echo "Creating post-install launch script $launch_script..."
    cat <<EOF > $launch_script
#!/bin/bash
while pgrep -fq Installer.app; do
    sleep 1
done
open -a "$shortcut_path"
EOF
    chmod +x $launch_script
    cat $launch_script

    nohup $launch_script &>/dev/null &
elif [[ -n "$(which gtk-launch)" ]]; then
    gtk-launch $(basename $shortcut_path)
else
    nohup $spy_exe &>/dev/null &
fi
