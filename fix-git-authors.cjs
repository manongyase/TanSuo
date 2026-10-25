// 重写所有 commit 的 author/committer 邮箱
const { execSync } = require('child_process')

const repo = 'D:\\前端_页面'

console.log('Rewriting all commit authors...')

// git filter-branch 通过 env-filter 批量改
const cmd = `cd "${repo}" && git filter-branch -f --env-filter "export GIT_AUTHOR_NAME='manongyase'; export GIT_AUTHOR_EMAIL='manongyase@gmail.com'; export GIT_COMMITTER_NAME='manongyase'; export GIT_COMMITTER_EMAIL='manongyase@gmail.com'" HEAD`

try {
  execSync(cmd, { stdio: 'inherit', timeout: 60000 })
  console.log('\n✅ Done! Checking...')
  console.log(execSync(`cd "${repo}" && git log --format="%h %an <%ae> %s"`, { encoding: 'utf8' }))
} catch (e) {
  console.error('Failed:', e.message)
}
