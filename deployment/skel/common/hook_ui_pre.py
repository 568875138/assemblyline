#/usr/bin/env python

from assemblyline.al.install import SiteInstaller


def execute(alsi):
    return install_ui_symlinks(alsi)


def install_ui_symlinks(alsi):
    alsi.symlink('private/ui/static/images', 'assemblyline/ui/static/images/private')
    alsi.symlink('private/ui/static/js', 'assemblyline/ui/static/js/private')
    alsi.symlink('private/ui/static/ng-template','assemblyline/ui/static/ng-template/private')
    alsi.symlink('private/ui/templates', 'assemblyline/ui/templates/private')
    alsi.milestone("Private preinstall UI symlinks established")

if __name__ == '__main__':
    installer = SiteInstaller()
    install_ui_symlinks(installer)

