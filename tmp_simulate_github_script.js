const fs = require('fs');

const OUTPUT = fs.existsSync('out.txt') ? fs.readFileSync('out.txt', 'utf8') : '';
const context = { repo: { owner: 'giladbarnea', repo: 'prin' } };

const github = {
  search: {
    issuesAndPullRequests: async ({ q }) => {
      return { data: { total_count: 1, items: [] } };
    },
  },
  issues: {
    update: async ({ owner, repo, issue_number, body }) => ({ data: {} }),
    create: async ({ owner, repo, title, body }) => ({ data: {} }),
  },
};

(async () => {
  const title = 'Automated: Branch cleanup candidates (dry-run)';
  const body = `Weekly dry-run found candidate branches.\n\nOutput:\n\n\`\`\`\n${OUTPUT}\n\`\`\`\n\nComment: '@Cursor run script with -s --execute then close this issue' to execute deletion including stale branches.`;
  const { data } = await github.search.issuesAndPullRequests({
    q: `repo:${context.repo.owner}/${context.repo.repo} is:issue is:open in:title "${title}"`
  });
  if (data.total_count > 0) {
    const issue = data.items[0];
    await github.issues.update({ owner: context.repo.owner, repo: context.repo.repo, issue_number: issue.number, body });
  } else {
    await github.issues.create({ owner: context.repo.owner, repo: context.repo.repo, title, body });
  }
})();

 
