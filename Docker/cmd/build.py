import configparser
import datetime

import docker

from cmd.base import Command


class BuildCommand(Command):
    name = 'build'

    def add_parser(self, subparsers):
        parser = subparsers.add_parser("build", help='Build image')
        parser.add_argument('-e', '--environment', choices=['prod', 'test', 'dev'], required=True,
                            help='Environment for resulting image')
        parser.add_argument('-t', '--tag', type=str, help='Tag in git repository', required=True)
        parser.add_argument('-f', '--force', action='store_true', help='Force building even image already exists')
        parser.add_argument('-i', '--image', choices=['builder', 'base', 'boot', 'nodeos', 'keos'],
                            help='Component to build')

    def get_credentials(self):
        credentials = configparser.ConfigParser()
        credentials.read("credentials.ini")
        return credentials['repository']

    def build(self, *args, **kwargs):
        need_build = kwargs.pop('rebuild') or not self.docker_api.image_exists(kwargs['tag'])

        if not need_build:
            print('Image "%s" already exists, omit image building...' % kwargs['tag'])
            return

        print("Start building \"%s\"" % kwargs['tag'])
        st = datetime.datetime.now()
        self.docker_api.client.images.build(*args, **kwargs)
        et = datetime.datetime.now()
        print("Complete \"%s\". Elapsed %s" % (kwargs['tag'], et - st))

    def build_builder(self, args):
        self.build(path='.', dockerfile=self.docker_api.get_dockerfile('Dockerfile.Builder'),
                   tag=self.docker_api.get_image_name('builder'), rebuild=args is not None)

    def build_base(self, args):
        credentials = self.get_credentials()
        self.build(path='.', dockerfile=self.docker_api.get_dockerfile('Dockerfile.Base'),
                   tag=self.docker_api.get_image_name('base', args.tag),
                   buildargs={
                       'branch': args.tag,
                       'login': credentials['login'],
                       'password': credentials['password'],
                       'environment': args.environment
                   }, rebuild=args.force)

    def build_boot(self, args):
        version = self.docker_api.get_tag_name(args.tag)
        self.build(path='.', dockerfile=self.docker_api.get_dockerfile('Dockerfile.Boot'),
                   tag=self.docker_api.get_image_name('boot', args.tag),
                   buildargs={
                       'version': version,
                       'environment': args.environment
                   }, rebuild=args.force)

    def build_nodeos(self, args):
        version = self.docker_api.get_tag_name(args.tag)
        self.build(path='.', dockerfile=self.docker_api.get_dockerfile('Dockerfile.Node'),
                   tag=self.docker_api.get_image_name('nodeos', args.tag),
                   buildargs={
                       'version': version
                   }, rebuild=args.force)

    def build_keos(self, args):
        version = self.docker_api.get_tag_name(args.tag)
        self.build(path='.', dockerfile=self.docker_api.get_dockerfile('Dockerfile.Keos'),
                   tag=self.docker_api.get_image_name('keos', args.tag),
                   buildargs={
                       'version': version
                   }, rebuild=args.force)

    def exec(self, args):
        if args.image:
            getattr(self, 'build_%s' % args.image)(args)
            return

        self.build_builder(None)
        self.build_base(args)
        self.build_boot(args)
        self.build_nodeos(args)
        self.build_keos(args)