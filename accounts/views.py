from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .models import get_profile


class SignupView(CreateView):
    """Local signup: creates the user, drops them in the ``user`` group, logs them in."""

    form_class = UserCreationForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.groups.add(Group.objects.get(name="user"))
        get_profile(self.object)
        login(self.request, self.object)
        return response


@login_required
def settings(request):
    """Profile + preferences. Role is shown read-only: never self-editable."""

    from .forms import ProfileForm, UserUpdateForm

    profile = get_profile(request.user)
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect("settings")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    groups = ", ".join(g.name for g in request.user.groups.all()) or "user"
    return render(
        request,
        "accounts/settings.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "role": groups,
        },
    )


def _require_staff(request):
    if not request.user.is_staff:
        raise Http404


@login_required
def user_list(request):
    """Staff-only roster. Usernames and standing only, never spending data."""

    _require_staff(request)
    users = (
        get_user_model()
        .objects.order_by("username")
        .prefetch_related("groups")
    )
    return render(request, "accounts/user_list.html", {"users": users})


@login_required
def user_toggle(request, pk):
    """Activate/deactivate an account. Self and superusers are protected."""

    _require_staff(request)
    target = get_object_or_404(get_user_model(), pk=pk)
    if request.method == "POST":
        if target.pk == request.user.pk or target.is_superuser:
            messages.error(
                request, "You cannot deactivate yourself or a superuser."
            )
        else:
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
    return redirect("user-list")
