#!/usr/bin/env bash
# ============================================================
# WSL (Ubuntu) 一键创建 front 用户，并在该用户下安装 nvm + Node.js LTS
#
# 用法:
#   sudo bash setup-node.sh    # 普通用户执行：自动创建/切换到 front 再安装
#   bash setup-node.sh         # root 执行：同上
#   bash setup-node.sh         # front 用户执行：直接装到自己家目录
#
# 说明:
#   - root 执行时，脚本会把安装动作切换到 front 用户身份（不是装在 root 下）
#   - 脚本幂等，可重复执行
#   - 可覆盖的环境变量:
#       FRONT_USER=front
#       FRONT_PASSWORD=xxx
#       NVM_NODEJS_ORG_MIRROR=https://nodejs.org/dist
#     示例: FRONT_USER=front FRONT_PASSWORD=123456 sudo -E bash setup-node.sh
# ============================================================
set +u

FRONT_USER="${FRONT_USER:-front}"
SELF="$(readlink -f "$0")"
NVM_VERSION="v0.40.1"
export NVM_NODEJS_ORG_MIRROR="${NVM_NODEJS_ORG_MIRROR:-https://npmmirror.com/mirrors/node}"

info() { printf '\033[1;32m[INFO]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[ERR ]\033[0m %s\n' "$*"; }

# ============================================================
# 阶段一：root 引导（创建 front 用户并切换身份）
# ============================================================
if [ "$(id -u)" -eq 0 ]; then
    if [ "${1:-}" = "--phase2" ]; then
        err "阶段二不允许以 root 身份执行"
        exit 1
    fi

    info "检测到 root 身份，目标用户: $FRONT_USER"

    # 1. 创建用户
    if id "$FRONT_USER" >/dev/null 2>&1; then
        info "用户 $FRONT_USER 已存在，跳过创建"
    else
        useradd -m -s /bin/bash "$FRONT_USER" || { err "创建用户 $FRONT_USER 失败"; exit 1; }
        info "已创建用户 $FRONT_USER"
    fi

    HOME_DIR="$(getent passwd "$FRONT_USER" | cut -d: -f6)"
    [ -z "$HOME_DIR" ] && HOME_DIR="/home/$FRONT_USER"
    if [ ! -d "$HOME_DIR" ]; then
        mkdir -p "$HOME_DIR"
        chown "$FRONT_USER:$FRONT_USER" "$HOME_DIR"
        info "已补建家目录 $HOME_DIR"
    fi

    # 2. 加入 sudo 组，方便后续自行维护
    if getent group sudo >/dev/null 2>&1; then
        usermod -aG sudo "$FRONT_USER" 2>/dev/null || true
    fi

    # 3. 设置密码：优先读 FRONT_PASSWORD，否则交互询问（回车跳过）
    if [ -n "${FRONT_PASSWORD:-}" ]; then
        echo "$FRONT_USER:$FRONT_PASSWORD" | chpasswd && info "已设置 $FRONT_USER 密码"
    elif [ -t 0 ]; then
        read -r -s -p "为 $FRONT_USER 设置登录密码（直接回车跳过）: " PW_INPUT
        echo ""
        if [ -n "$PW_INPUT" ]; then
            echo "$FRONT_USER:$PW_INPUT" | chpasswd && info "已设置 $FRONT_USER 密码"
        else
            warn "已跳过密码设置；之后可用 root 执行: passwd $FRONT_USER"
        fi
    else
        warn "未设置密码；之后可用 root 执行: passwd $FRONT_USER"
    fi

    # 4. 系统级依赖（装到系统目录，front 后续无需 sudo）
    MISSING=""
    for p in curl git xz-utils ca-certificates; do
        dpkg -s "$p" >/dev/null 2>&1 || MISSING="$MISSING $p"
    done
    if [ -n "$MISSING" ]; then
        info "安装系统依赖:$MISSING"
        if ! (apt-get update -qq && apt-get install -y $MISSING); then
            warn "依赖安装失败（可能无网络）。若后续报错，请手动执行:"
            warn "  apt-get install -y curl git xz-utils ca-certificates"
        fi
    fi

    # 5. 复制脚本到 /tmp 并交给 front，避免 /mnt 挂载盘权限与属主问题
    RUNNER="/tmp/setup-node-${FRONT_USER}.sh"
    cp "$SELF" "$RUNNER" && chown "$FRONT_USER:$FRONT_USER" "$RUNNER" && chmod 755 "$RUNNER"
    info "切换到 $FRONT_USER 身份执行安装 ..."
    echo "------------------------------------------------------------"

    if command -v runuser >/dev/null 2>&1; then
        runuser -l "$FRONT_USER" -c "bash '$RUNNER' --phase2"
    else
        su - "$FRONT_USER" -c "bash '$RUNNER' --phase2"
    fi
    RC=$?
    rm -f "$RUNNER"
    echo "------------------------------------------------------------"
    exit $RC
fi

# ============================================================
# 阶段二：以 target 用户身份安装（不能是 root）
# ============================================================
CUR_USER="$(id -un)"
if [ "$CUR_USER" != "$FRONT_USER" ]; then
    err "当前用户是 $CUR_USER，不是目标用户 $FRONT_USER"
    warn "请用 root/sudo 执行: sudo bash $SELF"
    warn "（脚本会自动创建 $FRONT_USER 并切换到该用户下安装）"
    exit 1
fi

info "当前用户: $CUR_USER    家目录: $HOME"

if ! command -v curl >/dev/null 2>&1; then
    err "缺少 curl。请先以 root 执行一次本脚本，或手动执行:"
    err "  apt-get install -y curl git xz-utils ca-certificates"
    exit 1
fi

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

load_nvm() {
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
}
load_nvm

# 1. 安装 nvm（GitHub -> gitee 脚本 -> git clone 三级回退）
if ! command -v nvm >/dev/null 2>&1; then
    INSTALLER="$(mktemp)"
    info "下载 nvm $NVM_VERSION 安装脚本（GitHub）..."
    if curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" -o "$INSTALLER"; then
        bash "$INSTALLER"
    else
        warn "GitHub 不可用，改用 gitee 镜像脚本..."
        if curl -fsSL "https://gitee.com/mirrors/nvm/raw/${NVM_VERSION}/install.sh" -o "$INSTALLER"; then
            bash "$INSTALLER"
        else
            warn "镜像脚本也不可用，改用 git clone..."
            if [ -d "$NVM_DIR/.git" ]; then
                git -C "$NVM_DIR" fetch --depth 1 origin tag "$NVM_VERSION" && \
                    git -C "$NVM_DIR" checkout -q "$NVM_VERSION"
            else
                git clone --depth 1 --branch "$NVM_VERSION" https://gitee.com/mirrors/nvm.git "$NVM_DIR"
            fi
        fi
    fi
    rm -f "$INSTALLER"
    load_nvm
fi

if ! command -v nvm >/dev/null 2>&1; then
    err "nvm 加载失败，请检查 $NVM_DIR/nvm.sh 是否存在"
    exit 1
fi
info "nvm 就绪: $(nvm --version)"

# 2. 保证 ~/.bashrc 有加载片段（git clone 兜底路径不会自动写入）
if ! grep -q 'nvm.sh' "$HOME/.bashrc" 2>/dev/null; then
    {
        echo ''
        echo '# nvm'
        echo 'export NVM_DIR="$HOME/.nvm"'
        echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"'
    } >> "$HOME/.bashrc"
    info "已写入 nvm 加载片段到 ~/.bashrc"
fi

# 3. 安装并启用 Node LTS
info "安装 Node.js LTS（下载源: $NVM_NODEJS_ORG_MIRROR）..."
nvm install --lts
nvm use --lts

# 4. 设为默认版本
CUR_VER="$(nvm current)"
nvm alias default "$CUR_VER" >/dev/null 2>&1
info "默认版本已设为 $CUR_VER"

# 5. 验证
echo ""
echo "==================== 验证结果 ===================="
echo "用户      : $(whoami)"
echo "家目录    : $HOME"
echo "nvm 版本  : $(nvm --version)"
echo "node 路径 : $(command -v node)"
echo "node 版本 : $(node -v)"
echo "npm  版本 : $(npm -v)"
node -e "console.log('Node 自检: OK, platform=' + process.platform + ', arch=' + process.arch)"
echo "=================================================="
echo ""
info "安装完成。验证方法:"
info "  su - $FRONT_USER"
info "  node -v && npm -v"
