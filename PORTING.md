# Porting Bosun to a new firm

Bosun carries no credentials and no environment-specific identifiers, so adopting it means adding
configuration, not editing code. Expect a working environment in a sandbox subscription within a day
of approvals, and a first live deal room within weeks, once the firm's own domains and glossary come
out of discovery.

## What you need

- Windows PowerShell 5.1 or later, Azure CLI and GitHub CLI
- A Global Administrator for the Entra ID tenant, to run bootstrap once
- Owner rights on an Azure subscription (a sandbox subscription is the right place to start)
- A GitHub organization to hold your copy

## Steps

1. **Create your copy.** On GitHub, choose *Use this template* and create a private repository in your
   organization. You get a clean history with nothing from the original.
2. **Add your firm profile.** Copy `config/profiles/contoso.yaml` to `config/profiles/<your-firm>.yaml`
   and replace the domains, personas and owners with your own. The prefix must be 2-9 lowercase
   letters or digits.
3. **Set your owners.** Replace the owner in `.github/CODEOWNERS` with your own reviewers, and the
   copyright holder in `LICENSE` if your organization requires it. These are the only two files allowed
   to name an organization or person.
4. **Fill in `.env`.** Copy `.env.example` to `.env` and fill it in. It is gitignored and holds no
   secrets.
5. **Run bootstrap** from your clone, as the Global Administrator:
   `powershell -ExecutionPolicy Bypass -File bootstrap/bootstrap.ps1`
   At the end it asks for deny-list terms: names that must never appear in the repository (former
   employers, client names, internal project names). They are stored only as a GitHub secret.
6. **Require approval for deploys.** In the repository, *Settings > Environments > production*, add
   required reviewers.
7. **Open your first pull request** with your profile. CI must pass every check before anything
   deploys.

## What bootstrap creates (for security review)

| Object | Where | Rights |
|--------|-------|--------|
| Resource group | Azure, the subscription you choose | Holds every platform resource |
| Deploy identity (app registration, no secrets) | Entra ID | Contributor on that one resource group only |
| Federated credentials | On the deploy identity | Trust only this repository's `production` environment and pull requests |
| Graph application permissions | On the deploy identity | Exactly those in `config/guardrails.yaml` (CI enforces this) |
| Repository variables, `production` environment, `DENYLIST` secret | GitHub | Configuration for the pipeline |

Bootstrap creates no passwords, keys or certificates. Removing the platform is the reverse: delete the
resource group and the app registration.
