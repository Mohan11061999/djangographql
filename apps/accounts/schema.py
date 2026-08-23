import graphene
import graphql_jwt
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from apps.core.permissions import login_required
from .models import Address, EmailVerificationToken, PasswordResetToken
from .notifications import send_password_reset_email, send_verification_email, send_welcome_email

User = get_user_model()


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone_number", "role", "is_email_verified", "created_at"]


class AddressType(DjangoObjectType):
    class Meta:
        model = Address
        fields = "__all__"


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
class AccountsQuery(graphene.ObjectType):
    me = graphene.Field(UserType)
    my_addresses = graphene.List(AddressType)

    @login_required
    def resolve_me(root, info):
        return info.context.user

    @login_required
    def resolve_my_addresses(root, info):
        return Address.objects.filter(user=info.context.user).order_by("-is_default", "-created_at")


# ---------------------------------------------------------------------------
# Auth mutations
# ---------------------------------------------------------------------------
class Register(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        first_name = graphene.String(required=True)
        last_name = graphene.String()
        phone_number = graphene.String()

    ok = graphene.Boolean()
    user = graphene.Field(UserType)

    def mutate(root, info, email, password, first_name, last_name="", phone_number=""):
        email = email.strip().lower()
        if User.objects.filter(email=email).exists():
            raise GraphQLError("An account with this email already exists.")

        try:
            password_validation.validate_password(password)
        except ValidationError as e:
            raise GraphQLError(" ".join(e.messages))

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )

        token = EmailVerificationToken.objects.create(
            user=user, expires_at=timezone.now() + timedelta(hours=24)
        )
        send_verification_email(user, token.token)
        send_welcome_email(user)

        return Register(ok=True, user=user)


class VerifyEmail(graphene.Mutation):
    class Arguments:
        token = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(root, info, token):
        try:
            record = EmailVerificationToken.objects.select_related("user").get(token=token)
        except EmailVerificationToken.DoesNotExist:
            raise GraphQLError("Invalid verification link.")

        if not record.is_valid:
            raise GraphQLError("This verification link has expired. Please request a new one.")

        record.is_used = True
        record.save(update_fields=["is_used"])

        user = record.user
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        return VerifyEmail(ok=True)


class ResendVerificationEmail(graphene.Mutation):
    ok = graphene.Boolean()

    @login_required
    def mutate(root, info):
        user = info.context.user
        if user.is_email_verified:
            raise GraphQLError("Email is already verified.")

        token = EmailVerificationToken.objects.create(
            user=user, expires_at=timezone.now() + timedelta(hours=24)
        )
        send_verification_email(user, token.token)
        return ResendVerificationEmail(ok=True)


class RequestPasswordReset(graphene.Mutation):
    """
    Always returns ok=True regardless of whether the email exists, to
    avoid leaking which emails are registered.
    """

    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(root, info, email):
        try:
            user = User.objects.get(email=email.strip().lower())
        except User.DoesNotExist:
            return RequestPasswordReset(ok=True)

        token = PasswordResetToken.objects.create(
            user=user, expires_at=timezone.now() + timedelta(hours=1)
        )
        send_password_reset_email(user, token.token)
        return RequestPasswordReset(ok=True)


class ResetPassword(graphene.Mutation):
    class Arguments:
        token = graphene.UUID(required=True)
        new_password = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(root, info, token, new_password):
        try:
            record = PasswordResetToken.objects.select_related("user").get(token=token)
        except PasswordResetToken.DoesNotExist:
            raise GraphQLError("Invalid or expired reset link.")

        if not record.is_valid:
            raise GraphQLError("This reset link has expired. Please request a new one.")

        try:
            password_validation.validate_password(new_password, user=record.user)
        except ValidationError as e:
            raise GraphQLError(" ".join(e.messages))

        user = record.user
        user.set_password(new_password)
        user.save(update_fields=["password"])

        record.is_used = True
        record.save(update_fields=["is_used"])

        # Invalidate any other outstanding reset tokens for this user.
        PasswordResetToken.objects.filter(user=user, is_used=False).exclude(pk=record.pk).update(is_used=True)

        return ResetPassword(ok=True)


class ChangePassword(graphene.Mutation):
    class Arguments:
        old_password = graphene.String(required=True)
        new_password = graphene.String(required=True)

    ok = graphene.Boolean()

    @login_required
    def mutate(root, info, old_password, new_password):
        user = info.context.user
        if not user.check_password(old_password):
            raise GraphQLError("Current password is incorrect.")

        try:
            password_validation.validate_password(new_password, user=user)
        except ValidationError as e:
            raise GraphQLError(" ".join(e.messages))

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return ChangePassword(ok=True)


class UpdateProfile(graphene.Mutation):
    class Arguments:
        first_name = graphene.String()
        last_name = graphene.String()
        phone_number = graphene.String()

    ok = graphene.Boolean()
    user = graphene.Field(UserType)

    @login_required
    def mutate(root, info, **kwargs):
        user = info.context.user
        for field, value in kwargs.items():
            if value is not None:
                setattr(user, field, value)
        user.save()
        return UpdateProfile(ok=True, user=user)


# ---------------------------------------------------------------------------
# Address mutations
# ---------------------------------------------------------------------------
class AddressInput(graphene.InputObjectType):
    label = graphene.String()
    full_name = graphene.String(required=True)
    phone_number = graphene.String(required=True)
    line1 = graphene.String(required=True)
    line2 = graphene.String()
    city = graphene.String(required=True)
    state = graphene.String(required=True)
    postal_code = graphene.String(required=True)
    country = graphene.String()
    is_default = graphene.Boolean()


class AddAddress(graphene.Mutation):
    class Arguments:
        input = AddressInput(required=True)

    ok = graphene.Boolean()
    address = graphene.Field(AddressType)

    @login_required
    def mutate(root, info, input):
        address = Address.objects.create(user=info.context.user, **input)
        return AddAddress(ok=True, address=address)


class UpdateAddress(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = AddressInput(required=True)

    ok = graphene.Boolean()
    address = graphene.Field(AddressType)

    @login_required
    def mutate(root, info, id, input):
        try:
            address = Address.objects.get(id=id, user=info.context.user)
        except Address.DoesNotExist:
            raise GraphQLError("Address not found.")

        for field, value in input.items():
            if value is not None:
                setattr(address, field, value)
        address.save()
        return UpdateAddress(ok=True, address=address)


class DeleteAddress(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @login_required
    def mutate(root, info, id):
        deleted, _ = Address.objects.filter(id=id, user=info.context.user).delete()
        if not deleted:
            raise GraphQLError("Address not found.")
        return DeleteAddress(ok=True)


class SetDefaultAddress(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @login_required
    def mutate(root, info, id):
        try:
            address = Address.objects.get(id=id, user=info.context.user)
        except Address.DoesNotExist:
            raise GraphQLError("Address not found.")
        address.is_default = True
        address.save()  # model.save() unsets other defaults for this user
        return SetDefaultAddress(ok=True)


class AccountsMutation(graphene.ObjectType):
    # JWT auth (login/refresh/verify token) provided by django-graphql-jwt
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()

    register = Register.Field()
    verify_email = VerifyEmail.Field()
    resend_verification_email = ResendVerificationEmail.Field()
    request_password_reset = RequestPasswordReset.Field()
    reset_password = ResetPassword.Field()
    change_password = ChangePassword.Field()
    update_profile = UpdateProfile.Field()

    add_address = AddAddress.Field()
    update_address = UpdateAddress.Field()
    delete_address = DeleteAddress.Field()
    set_default_address = SetDefaultAddress.Field()
